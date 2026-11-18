"""Gestión de datasets: carga masiva, formulario, versiones, EDA, limpieza y selección de variables."""

from __future__ import annotations

import io
import json
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ecnt_api.db import get_db
from ecnt_api.orm import Dataset, DatasetVersion, Usuario
from ecnt_api.security import RESEARCH, require_roles
from ecnt_api.services import datasets as svc
from ecnt_api.utils import audit, clean_json
from ecnt_core import eda, features, plots, splitting
from ecnt_core.experiment import default_features
from ecnt_core.schemas import DEFAULT_TARGET
from ecnt_core.validation import validate

router = APIRouter(prefix="/datasets", tags=["datasets"])
Researcher = Depends(require_roles(*RESEARCH))


class RecordsIn(BaseModel):
    registros: list[dict[str, Any]] = Field(min_length=1, max_length=500)


class NewFormDataset(RecordsIn):
    nombre: str = Field(min_length=2, max_length=200)
    fuente: str = ""
    descripcion: str = ""
    rol: str | None = None
    es_sintetico: bool = False


class CleanIn(BaseModel):
    pasos: list[dict[str, Any]] = Field(min_length=1)
    descripcion: str = ""


class FeaturesIn(BaseModel):
    objetivo: str = DEFAULT_TARGET
    variables: list[str] | None = None
    proporcion: str = "80/20"
    semilla: int = 42
    estrategia: str = "aleatoria"
    columna_grupo: str | None = None


def _version(db: Session, version_id: int) -> DatasetVersion:
    v = db.get(DatasetVersion, version_id)
    if v is None:
        raise HTTPException(404, "Versión de dataset no encontrada")
    return v


def _fig(fig) -> dict:
    return json.loads(fig.to_json())


@router.get("")
def list_datasets(db: Session = Depends(get_db), _: Usuario = Researcher):
    return [svc.dataset_dict(d) for d in db.scalars(select(Dataset).order_by(Dataset.id.desc())).all()]


@router.post("/upload", status_code=201)
async def upload(request: Request, archivo: UploadFile = File(...), nombre: str = Form(...), fuente: str = Form(""),
                 descripcion: str = Form(""), rol: str | None = Form(None), es_sintetico: bool = Form(False),
                 db: Session = Depends(get_db), user: Usuario = Researcher):
    content = await archivo.read()
    if len(content) > request.app.state.settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Archivo demasiado grande")
    ds, v = svc.create_from_upload(db, request.app.state.storage, user, content, archivo.filename or "archivo.csv",
                                   nombre, fuente, descripcion, rol or None, es_sintetico)
    audit(db, user, "cargar_dataset", f"dataset:{ds.id}", {"archivo": archivo.filename, "filas": v.filas}, request)
    db.commit()
    return {"dataset": svc.dataset_dict(ds), "version": svc.version_dict(v)}


@router.post("/validate")
async def validate_only(archivo: UploadFile = File(...), _: Usuario = Researcher):
    """Valida un archivo sin guardarlo (vista previa antes de cargar)."""
    from ecnt_core.io import read_table
    df = read_table(await archivo.read(), archivo.filename or "archivo.csv")
    return {"vista_previa": clean_json(df.head(20)), "columnas": list(df.columns),
            "validacion": clean_json(validate(df).to_dict())}


@router.post("/form", status_code=201)
def create_from_form(body: NewFormDataset, request: Request, db: Session = Depends(get_db),
                     user: Usuario = Researcher):
    ds, v = svc.create_from_records(db, request.app.state.storage, user, body.registros, body.nombre, body.fuente,
                                    body.descripcion, body.rol, body.es_sintetico)
    audit(db, user, "crear_dataset_formulario", f"dataset:{ds.id}", {"registros": len(body.registros)}, request)
    db.commit()
    return {"dataset": svc.dataset_dict(ds), "version": svc.version_dict(v)}


@router.get("/{dataset_id}")
def get_dataset(dataset_id: int, db: Session = Depends(get_db), _: Usuario = Researcher):
    ds = db.get(Dataset, dataset_id)
    if ds is None:
        raise HTTPException(404, "Dataset no encontrado")
    return svc.dataset_dict(ds)


@router.get("/versions/{version_id}")
def get_version(version_id: int, db: Session = Depends(get_db), _: Usuario = Researcher):
    return svc.version_dict(_version(db, version_id))


@router.get("/versions/{version_id}/rows")
def rows(version_id: int, request: Request, offset: int = 0, limit: int = 100, db: Session = Depends(get_db),
         _: Usuario = Researcher):
    df = svc.load_df(request.app.state.storage, _version(db, version_id))
    limit = max(1, min(limit, 1000))
    return {"total": len(df), "columnas": list(df.columns), "filas": clean_json(df.iloc[offset:offset + limit])}


@router.get("/versions/{version_id}/download")
def download(version_id: int, request: Request, db: Session = Depends(get_db), user: Usuario = Researcher):
    v = _version(db, version_id)
    df = svc.load_df(request.app.state.storage, v)
    audit(db, user, "descargar_dataset", f"dataset_version:{v.id}", request=request)
    db.commit()
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    filename = f"dataset_{v.dataset_id}_v{v.numero}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.post("/versions/{version_id}/records", status_code=201)
def add_records(version_id: int, body: RecordsIn, request: Request, db: Session = Depends(get_db),
                user: Usuario = Researcher):
    v = svc.add_records(db, request.app.state.storage, user, _version(db, version_id), body.registros)
    audit(db, user, "agregar_registros", f"dataset_version:{v.id}", {"registros": len(body.registros)}, request)
    db.commit()
    return svc.version_dict(v)


@router.post("/versions/{version_id}/clean", status_code=201)
def clean(version_id: int, body: CleanIn, request: Request, db: Session = Depends(get_db), user: Usuario = Researcher):
    v = svc.clean_version(db, request.app.state.storage, user, _version(db, version_id), body.pasos, body.descripcion)
    audit(db, user, "limpiar_dataset", f"dataset_version:{v.id}", {"pasos": [p.get("op") for p in body.pasos]}, request)
    db.commit()
    return svc.version_dict(v)


# ------------------------------- EDA ----------------------------------------
@router.get("/versions/{version_id}/eda")
def eda_summary(version_id: int, request: Request, db: Session = Depends(get_db), _: Usuario = Researcher):
    df = svc.load_df(request.app.state.storage, _version(db, version_id))
    return clean_json({
        "calidad": eda.quality_summary(df),
        "validacion": validate(df).to_dict(),
        "descriptivas": eda.numeric_summary(df),
        "categoricas": eda.categorical_columns(df),
        "numericas": eda.numeric_columns(df),
    })


@router.get("/versions/{version_id}/eda/frequencies")
def eda_frequencies(version_id: int, column: str, request: Request, db: Session = Depends(get_db),
                    _: Usuario = Researcher):
    df = svc.load_df(request.app.state.storage, _version(db, version_id))
    if column not in df:
        raise HTTPException(400, f"Columna inexistente: {column}")
    f = eda.frequencies(df, column)
    return {"tabla": clean_json(f), "grafico": _fig(plots.frequency_bar(f, column))}


@router.get("/versions/{version_id}/eda/correlation")
def eda_correlation(version_id: int, request: Request, method: str = "spearman", target: str | None = None,
                    db: Session = Depends(get_db), _: Usuario = Researcher):
    if method not in ("spearman", "pearson", "kendall"):
        raise HTTPException(400, "Método inválido")
    df = svc.load_df(request.app.state.storage, _version(db, version_id))
    corr = eda.correlation_matrix(df, method)
    out = {"matriz": clean_json(corr.reset_index().rename(columns={"index": "variable"})),
           "grafico": _fig(plots.correlation_heatmap(corr, f"Matriz de correlación ({method})"))}
    if target and target in df:
        out["con_objetivo"] = clean_json(eda.target_correlations(df, target, method))
    return out


@router.get("/versions/{version_id}/eda/plot")
def eda_plot(version_id: int, kind: str, request: Request, column: str | None = None, group: str | None = None,
             target: str | None = None, db: Session = Depends(get_db), _: Usuario = Researcher):
    df = svc.load_df(request.app.state.storage, _version(db, version_id))
    for c in (column, group, target):
        if c and c not in df:
            raise HTTPException(400, f"Columna inexistente: {c}")
    if kind == "histogram" and column:
        fig = plots.histogram(df, column)
    elif kind == "box" and column and group:
        fig = plots.boxplot_by_group(df, column, group)
    elif kind == "scatter" and column and target:
        fig = plots.scatter_vs_target(df, column, target, group)
    elif kind == "missing":
        fig = plots.missing_bar(df)
    else:
        raise HTTPException(400, "Combinación de gráfico inválida (histogram+column, box+column+group, "
                                 "scatter+column+target, missing)")
    return _fig(fig)


@router.post("/versions/{version_id}/features")
def feature_analysis(version_id: int, body: FeaturesIn, request: Request, db: Session = Depends(get_db),
                     _: Usuario = Researcher):
    """Ranking, VIF y regresión OLS calculados SOLO con la partición de entrenamiento (sin fuga)."""
    df = svc.load_df(request.app.state.storage, _version(db, version_id))
    if body.objetivo not in df:
        raise HTTPException(400, f"No existe la variable objetivo '{body.objetivo}'")
    df = df[df[body.objetivo].notna()]
    feats = body.variables or default_features(df, body.objetivo)
    split = splitting.make_split(df, body.proporcion, body.semilla, body.estrategia, group_col=body.columna_grupo,
                                 stratify_target=body.objetivo if body.estrategia == "aleatoria" else None)
    train, _test = split.apply(df)
    ranking = features.rank_features(train[feats], train[body.objetivo], body.semilla)
    ols, ols_s = features.ols_table(train[feats], train[body.objetivo])
    corr = eda.correlation_matrix(train, "spearman", [*feats, body.objetivo])
    return clean_json({
        "n_entrenamiento": len(train), "n_prueba_excluida": len(_test),
        "ranking": ranking, "vif": features.vif(train[feats]), "ols": ols, "ols_resumen": ols_s,
        "grafico_correlacion": _fig(plots.correlation_heatmap(corr, "Correlación (solo entrenamiento)")),
        "grafico_ranking": _fig(plots.feature_importance_bar(
            ranking.assign(importancia=ranking["importancia_rf"]), title="Importancia RF (entrenamiento)")),
    })
