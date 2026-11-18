"""Experimentos, versiones de modelo, aprobación/publicación y predicciones territoriales."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import KFold, cross_val_predict
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ecnt_api.orm import DatasetVersion, Experimento, Prediccion, Usuario, VersionModelo
from ecnt_api.services.datasets import load_df
from ecnt_api.utils import Storage, clean_json
from ecnt_core import evaluation, registry
from ecnt_core.experiment import ExperimentConfig, run_experiment
from ecnt_core.models import ALGORITHMS

LEVELS = ["muy bajo", "bajo", "medio", "alto", "muy alto"]


class ModelStateError(ValueError):
    pass


def _config(cfg: dict) -> ExperimentConfig:
    allowed = set(ExperimentConfig.__dataclass_fields__)
    unknown = set(cfg) - allowed
    if unknown:
        raise ValueError(f"Parámetros de configuración desconocidos: {sorted(unknown)}")
    return ExperimentConfig(**cfg)


def run_and_store(db: Session, storage: Storage, user: Usuario, version: DatasetVersion, cfg: dict,
                  group: str | None = None) -> tuple[Experimento, VersionModelo]:
    df = load_df(storage, version)
    result = run_experiment(df, _config(cfg))
    s = clean_json(result.summary)
    s["predicciones_prueba"] = clean_json(result.predictions)
    s["ranking_entrenamiento"] = clean_json(result.ranking)
    exp = Experimento(dataset_version_id=version.id, grupo_comparacion=group, algoritmo=s["algoritmo"],
                      objetivo=s["objetivo"], config=clean_json(result.config), resumen=s,
                      rmse_cv=s["rmse_cv_media"], rmse_test=s["rmse_test"], r2_test=s["r2_test"], creado_por=user.id)
    db.add(exp)
    db.flush()
    path = registry.save_bundle(result, storage.model_dir(exp.id), version=f"exp-{exp.id}",
                                extra={"dataset_version_id": version.id})
    meta = registry.load_bundle(path).metadata
    mv = VersionModelo(experimento_id=exp.id, nombre=f"{ALGORITHMS[s['algoritmo']].name} · exp {exp.id}",
                       algoritmo=s["algoritmo"], objetivo=s["objetivo"], ruta=storage.rel(path),
                       sha256=meta["sha256_modelo"])
    db.add(mv)
    db.flush()
    return exp, mv


def compare(db: Session, storage: Storage, user: Usuario, version: DatasetVersion, base_cfg: dict,
            algorithms: list[str], params: dict[str, dict] | None = None) -> dict:
    """Entrena varios algoritmos con la MISMA partición/variables/semilla (hiperparámetros propios de cada uno)."""
    group = uuid.uuid4().hex[:12]
    params = params or {}
    rows = []
    created = []
    for a in algorithms:
        exp, mv = run_and_store(db, storage, user, version,
                                {**base_cfg, "algorithm": a, "params": params.get(a, {})}, group)
        s = exp.resumen
        rows.append({"experimento_id": exp.id, "version_modelo_id": mv.id, **{k: s[k] for k in (
            "algoritmo", "nombre", "rmse_cv_media", "rmse_cv_de", "mae_cv_media", "r2_cv_media", "rmse_test",
            "mae_test", "r2_test", "rmse_entrenamiento", "n_pliegues")}})
        created.append(exp)
    choice = evaluation.select_best_model(rows, {k: a.complexity for k, a in ALGORITHMS.items()})
    for exp in created:
        exp.resumen = {**exp.resumen, "seleccion_grupo": choice}
    return clean_json({"grupo": group, "tabla": rows, "seleccion": choice})


def bundle(storage: Storage, mv: VersionModelo) -> registry.ModelBundle:
    return registry.load_bundle(storage.abs(mv.ruta))


def approve(db: Session, mv: VersionModelo, user: Usuario, nota: str) -> VersionModelo:
    if mv.estado != "evaluado":
        raise ModelStateError(f"Solo se aprueban modelos en estado 'evaluado' (actual: {mv.estado})")
    if not nota or len(nota.strip()) < 10:
        raise ModelStateError("La aprobación requiere una justificación (mínimo 10 caracteres)")
    s = mv.experimento.resumen
    if s.get("seleccion_grupo", {}).get("elegido") is None and "seleccion_grupo" in s:
        raise ModelStateError("Ningún modelo del grupo superó la línea base; no se puede aprobar")
    if mv.algoritmo == "baseline":
        raise ModelStateError("La línea base es solo un referente; no se publica")
    mv.estado, mv.aprobado_por, mv.aprobado_en, mv.nota_aprobacion = "aprobado", user.id, datetime.now(UTC), nota
    return mv


def _levels(values: pd.Series) -> pd.Series:
    try:
        return pd.qcut(values, 5, labels=LEVELS).astype(str)
    except ValueError:
        return pd.Series("medio", index=values.index)


def territorial_predictions(storage: Storage, mv: VersionModelo, version: DatasetVersion) -> pd.DataFrame:
    """Predicciones para todos los territorios del dataset del modelo.

    Para territorios con valor observado se usa la predicción FUERA DE MUESTRA (validación cruzada
    de 5 pliegues), para que comparar observado vs. esperado sea honesto (sin sobreajuste).
    """
    b = bundle(storage, mv)
    df = load_df(storage, version)
    meta = b.metadata
    target = meta["objetivo"]
    feats = b.features
    X = df[feats].copy()
    for c in meta["variables"]:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    y = pd.to_numeric(df[target], errors="coerce") if target in df else pd.Series(np.nan, index=df.index)
    pred = pd.Series(b.pipeline.predict(X), index=df.index)
    tipo = pd.Series("prediccion_modelo", index=df.index)
    has_y = y.notna()
    if has_y.sum() >= 10:
        oof = cross_val_predict(clone(b.pipeline), X[has_y], y[has_y],
                                cv=KFold(5, shuffle=True, random_state=meta["config"]["seed"]))
        pred[has_y] = oof
        tipo[has_y] = "fuera_de_muestra"
    q = float(meta["semiancho_intervalo_90"])
    out = pd.DataFrame({
        "divipola": df["divipola"].astype(str),
        "municipio": df.get("municipio", pd.Series("", index=df.index)).astype(str),
        "departamento": df.get("departamento", pd.Series("", index=df.index)).astype(str),
        "periodo": df.get("periodo", pd.Series("", index=df.index)).astype(str),
        "poblacion": pd.to_numeric(df["poblacion_2018"], errors="coerce") if "poblacion_2018" in df else np.nan,
        "observado": y,
        "predicho": pred,
        "lim_inf": np.maximum(pred - q, 0),
        "lim_sup": pred + q,
        "tipo": tipo,
    })
    out["nivel"] = _levels(out["predicho"])
    out["determinantes"] = clean_json(df[meta["variables"]].to_dict("records"))
    return out


def publish(db: Session, storage: Storage, mv: VersionModelo, user: Usuario) -> dict:
    if mv.estado != "aprobado":
        raise ModelStateError("Solo se publican modelos aprobados (validación humana previa)")
    prev = db.scalars(select(VersionModelo).where(VersionModelo.estado == "publicado",
                                                  VersionModelo.objetivo == mv.objetivo)).all()
    for p in prev:
        p.estado = "retirado"
    version = db.get(DatasetVersion, mv.experimento.dataset_version_id)
    preds = territorial_predictions(storage, mv, version)
    db.execute(delete(Prediccion).where(Prediccion.version_modelo_id == mv.id))
    for r in preds.to_dict("records"):
        db.add(Prediccion(version_modelo_id=mv.id, **clean_json(r)))
    mv.estado, mv.publicado_en = "publicado", datetime.now(UTC)
    db.flush()
    return {"publicado": mv.id, "retirados": [p.id for p in prev], "predicciones": len(preds)}


def retire(mv: VersionModelo) -> VersionModelo:
    if mv.estado == "retirado":
        raise ModelStateError("El modelo ya está retirado")
    mv.estado = "retirado"
    return mv


def published_model(db: Session, objetivo: str | None = None) -> VersionModelo | None:
    q = select(VersionModelo).where(VersionModelo.estado == "publicado")
    if objetivo:
        q = q.where(VersionModelo.objetivo == objetivo)
    return db.scalars(q.order_by(VersionModelo.publicado_en.desc())).first()


def predict_new(storage: Storage, mv: VersionModelo, df: pd.DataFrame) -> dict:
    """Pruebas con datos nuevos (Módulo 8): aplica las transformaciones del modelo y, si el archivo trae
    la variable objetivo, calcula métricas de desempeño independientes."""
    b = bundle(storage, mv)
    pred = registry.predict(b, df)
    target = b.metadata["objetivo"]
    out = {"n": len(pred), "predicciones": clean_json(pred)}
    if target in df.columns:
        y = pd.to_numeric(df[target], errors="coerce")
        mask = y.notna().values
        if mask.sum() >= 2:
            out["metricas"] = clean_json(evaluation.metrics(y[mask], pred["prediccion"][mask]))
            inside = (y[mask].values >= pred["lim_inf_90"][mask].values) & (
                y[mask].values <= pred["lim_sup_90"][mask].values)
            out["cobertura_intervalo_90"] = float(inside.mean())
            out["n_con_objetivo"] = int(mask.sum())
    train_ids = set(b.metadata["particion"]["train_ids"]) | set(b.metadata["particion"]["test_ids"])
    if "divipola" in df.columns:
        out["territorios_vistos_en_entrenamiento"] = int(df["divipola"].astype(str).isin(train_ids).sum())
    return out


def model_dict(mv: VersionModelo, full: bool = False) -> dict:
    s = mv.experimento.resumen
    d = {
        "id": mv.id, "nombre": mv.nombre, "algoritmo": mv.algoritmo, "objetivo": mv.objetivo, "estado": mv.estado,
        "experimento_id": mv.experimento_id, "dataset_version_id": mv.experimento.dataset_version_id,
        "sha256": mv.sha256, "creado": mv.creado, "aprobado_por": mv.aprobado_por, "aprobado_en": mv.aprobado_en,
        "nota_aprobacion": mv.nota_aprobacion, "publicado_en": mv.publicado_en,
        "metricas": {k: s.get(k) for k in ("rmse_cv_media", "rmse_cv_de", "r2_cv_media", "mae_test", "rmse_test",
                                            "r2_test", "semiancho_intervalo_90")},
        "variables": s.get("variables"), "es_sintetico": s.get("es_sintetico"),
    }
    if full:
        d["resumen"] = {k: v for k, v in s.items() if k not in ("predicciones_prueba", "ranking_entrenamiento")}
    return clean_json(d)


def experiment_dict(e: Experimento, full: bool = False) -> dict:
    d = {"id": e.id, "dataset_version_id": e.dataset_version_id, "grupo_comparacion": e.grupo_comparacion,
         "algoritmo": e.algoritmo, "objetivo": e.objetivo, "rmse_cv": e.rmse_cv, "rmse_test": e.rmse_test,
         "r2_test": e.r2_test, "estado": e.estado, "creado": e.creado}
    if full:
        d["config"] = e.config
        d["resumen"] = e.resumen
    return clean_json(d)
