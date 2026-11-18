"""Consultas territoriales para el ambiente EPS (solo lectura, datos agregados)."""

from __future__ import annotations

from functools import lru_cache

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ecnt_api.orm import Alerta, Prediccion, VersionModelo
from ecnt_api.services.datasets import latest_version_by_role
from ecnt_api.services.modeling import LEVELS
from ecnt_api.utils import Storage, clean_json
from ecnt_core.config import ROOT
from ecnt_core.schemas import CANONICAL, describe_column
from ecnt_core.sources.dane import read_divipola_coords

COORDS_FILE = ROOT / "data" / "external" / "divipola" / "divipola_municipios.json"


@lru_cache(maxsize=1)
def _coords() -> dict[str, tuple[float, float]]:
    """Coordenadas de cabeceras municipales (opcional: si el archivo no existe, no hay mapa)."""
    if not COORDS_FILE.exists():
        return {}
    c = read_divipola_coords(COORDS_FILE)
    return {r.divipola: (float(r.lat), float(r.lon)) for r in c.itertuples()}


def _with_coords(df: pd.DataFrame) -> pd.DataFrame:
    coords = _coords()
    return df.assign(lat=df["divipola"].map({k: v[0] for k, v in coords.items()}),
                     lon=df["divipola"].map({k: v[1] for k, v in coords.items()}))


DISCLAIMER = ("Herramienta de apoyo a la planificación en salud pública. Las estimaciones son territoriales y "
              "no constituyen diagnósticos individuales. La mortalidad registrada puede estar afectada por "
              "subregistro, en especial en zonas rurales dispersas.")


PRED_COLS = ("divipola", "municipio", "departamento", "periodo", "poblacion", "observado", "predicho", "lim_inf",
             "lim_sup", "nivel", "tipo")


def predictions_df(db: Session, mv: VersionModelo, with_determinants: bool = False) -> pd.DataFrame:
    """Predicciones del modelo en UNA consulta de columnas (sin materializar objetos ORM)."""
    cols = [getattr(Prediccion, c) for c in PRED_COLS]
    if with_determinants:
        cols.append(Prediccion.determinantes)
    rows = db.execute(select(*cols).where(Prediccion.version_modelo_id == mv.id)).all()
    df = pd.DataFrame(rows, columns=[*PRED_COLS, *(["determinantes"] if with_determinants else [])])
    if with_determinants and not df.empty:
        dets = pd.DataFrame(df.pop("determinantes").tolist(), index=df.index)
        df = pd.concat([df, dets], axis=1)
    return df


@lru_cache(maxsize=4)
def _load_cached(path: str, sha: str) -> pd.DataFrame:  # la huella invalida la caché si cambia la versión
    return pd.read_parquet(path)


def _panel(db: Session, storage: Storage) -> pd.DataFrame | None:
    """Panel histórico para la EPS: SIEMPRE la versión original (datos oficiales tal como se cargaron).

    Las versiones de limpieza son exploratorias del investigador y no deben alterar lo que ve la EPS
    (p. ej. una eliminación de duplicados con una llave equivocada). Para actualizar el panel de la EPS
    se carga un nuevo dataset con rol 'panel'.
    """
    v = latest_version_by_role(db, "panel")
    if v is None:
        return None
    original = v.dataset.versiones[0]
    return _load_cached(str(storage.abs(original.ruta)), original.sha256)


def dashboard(db: Session, storage: Storage, mv: VersionModelo) -> dict:
    p = predictions_df(db, mv)
    pop = p["poblacion"].fillna(0)
    weighted = float((p["predicho"] * pop).sum() / pop.sum()) if pop.sum() else None
    dist = p["nivel"].value_counts().reindex(LEVELS, fill_value=0)
    by_dep = (p.groupby("departamento")
              .agg(territorios=("divipola", "count"), poblacion=("poblacion", "sum"),
                   predicho_medio=("predicho", "mean"), observado_medio=("observado", "mean"))
              .reset_index().sort_values("predicho_medio", ascending=False))
    top = p.sort_values("predicho", ascending=False).head(10)
    evolution = None
    panel = _panel(db, storage)
    if panel is not None and "tasa_ecnt_std" in panel:
        pw = panel.assign(_w=panel.tasa_ecnt_std * panel.pob_total,
                          _p=panel.pob_total.where(panel.tasa_ecnt_std.notna()))
        g = pw.groupby("anio")
        evolution = pd.DataFrame({"tasa_mediana": g.tasa_ecnt_std.median(),
                                  "tasa_ponderada": g._w.sum() / g._p.sum(),
                                  "defunciones_ecnt": g.def_ecnt.sum()}).reset_index()
    alerts = db.execute(select(Alerta.prioridad, func.count()).where(Alerta.estado.not_in(["cerrada", "descartada"]))
                        .group_by(Alerta.prioridad)).all()
    resto = None
    if panel is not None and {"pob_resto", "pob_total", "anio"} <= set(panel.columns):
        last = panel[panel.anio == panel.anio.min()]
        resto = float(last.pob_resto.sum())
    return clean_json({
        "modelo": {"id": mv.id, "nombre": mv.nombre, "objetivo": mv.objetivo, "publicado_en": mv.publicado_en},
        "objetivo_descripcion": CANONICAL.get(mv.objetivo).description if mv.objetivo in CANONICAL else mv.objetivo,
        "total_territorios": len(p),
        "poblacion_total": float(pop.sum()),
        "poblacion_rural_dispersa_y_centros_poblados": resto,
        "tasa_esperada_ponderada": weighted,
        "tasa_observada_mediana": float(p["observado"].median()) if p["observado"].notna().any() else None,
        "distribucion_niveles": [{"nivel": k, "territorios": int(v)} for k, v in dist.items()],
        "por_departamento": by_dep,
        "top_territorios": top,
        "evolucion": evolution,
        "alertas_abiertas": {k: v for k, v in alerts},
        "aviso": DISCLAIMER,
    })


def list_territories(db: Session, mv: VersionModelo, departamento: str | None = None,
                     nivel: str | None = None, with_determinants: bool = False) -> list[dict]:
    p = predictions_df(db, mv, with_determinants)
    if departamento:
        p = p[p.departamento == departamento]
    if nivel:
        p = p[p.nivel == nivel]
    return clean_json(_with_coords(p).sort_values(["departamento", "municipio"]))


def territory_detail(db: Session, storage: Storage, mv: VersionModelo, divipola: str, role: str,
                     min_cell: int) -> dict | None:
    pred = db.scalars(select(Prediccion).where(Prediccion.version_modelo_id == mv.id,
                                               Prediccion.divipola == divipola)).first()
    if pred is None:
        return None
    dets = [{**describe_column(k), "valor": v} for k, v in pred.determinantes.items()]
    history = []
    panel = _panel(db, storage)
    if panel is not None:
        h = panel[panel.divipola.astype(str) == divipola].sort_values("anio")
        for r in h.to_dict("records"):
            n = r.get("def_ecnt")
            suppressed = role == "eps" and n is not None and n < min_cell
            history.append({"anio": r["anio"], "tasa_ecnt_std": r.get("tasa_ecnt_std"),
                            "tasa_ecnt_cruda": r.get("tasa_ecnt_cruda"),
                            "defunciones_ecnt": None if suppressed else n,
                            "conteo_suprimido": suppressed, "poblacion": r.get("pob_total"),
                            "pob_resto": r.get("pob_resto"), "periodo_pandemia": r.get("periodo_pandemia")})
    alerts = db.scalars(select(Alerta).where(Alerta.divipola == divipola).order_by(Alerta.id.desc())).all()
    lat, lon = _coords().get(divipola, (None, None))
    return clean_json({
        "divipola": pred.divipola, "municipio": pred.municipio, "departamento": pred.departamento,
        "lat": lat, "lon": lon,
        "periodo": pred.periodo, "poblacion": pred.poblacion, "observado": pred.observado, "predicho": pred.predicho,
        "lim_inf": pred.lim_inf, "lim_sup": pred.lim_sup, "nivel": pred.nivel, "tipo_prediccion": pred.tipo,
        "determinantes": dets, "historial": history,
        "alertas": [{"id": a.id, "titulo": a.titulo, "estado": a.estado, "prioridad": a.prioridad} for a in alerts],
        "aviso": DISCLAIMER,
    })


def compare_territories(db: Session, mv: VersionModelo, ids: list[str]) -> list[dict]:
    rows = db.scalars(select(Prediccion).where(Prediccion.version_modelo_id == mv.id,
                                               Prediccion.divipola.in_(ids))).all()
    return clean_json([{"divipola": r.divipola, "municipio": r.municipio, "departamento": r.departamento,
                        "observado": r.observado, "predicho": r.predicho, "lim_inf": r.lim_inf, "lim_sup": r.lim_sup,
                        "nivel": r.nivel, "poblacion": r.poblacion, **r.determinantes} for r in rows])
