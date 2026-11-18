"""Entrenamiento y comparación de modelos (solo administrador e investigador)."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ecnt_api.db import get_db
from ecnt_api.orm import DatasetVersion, Experimento, Usuario
from ecnt_api.security import RESEARCH, require_roles
from ecnt_api.services import modeling as svc
from ecnt_api.utils import audit, clean_json
from ecnt_core import plots

router = APIRouter(prefix="/experiments", tags=["experimentos"])
Researcher = Depends(require_roles(*RESEARCH))


class ExperimentIn(BaseModel):
    dataset_version_id: int
    config: dict[str, Any] = Field(default_factory=dict,
                                   description="Campos de ecnt_core.experiment.ExperimentConfig")


class CompareIn(BaseModel):
    dataset_version_id: int
    config: dict[str, Any] = Field(default_factory=dict)
    algoritmos: list[str] = Field(default=["baseline", "linear", "ridge", "random_forest", "gradient_boosting"],
                                  min_length=2)
    parametros: dict[str, dict[str, Any]] = Field(default_factory=dict,
                                                  description="Hiperparámetros por algoritmo (opcional)")


def _dv(db: Session, vid: int) -> DatasetVersion:
    v = db.get(DatasetVersion, vid)
    if v is None:
        raise HTTPException(404, "Versión de dataset no encontrada")
    return v


def _fig(fig) -> dict:
    return json.loads(fig.to_json())


@router.post("", status_code=201)
def create(body: ExperimentIn, request: Request, db: Session = Depends(get_db), user: Usuario = Researcher):
    if "algorithm" not in body.config:
        raise HTTPException(400, "Indique config.algorithm")
    exp, mv = svc.run_and_store(db, request.app.state.storage, user, _dv(db, body.dataset_version_id), body.config)
    audit(db, user, "entrenar_modelo", f"experimento:{exp.id}", {"algoritmo": exp.algoritmo}, request)
    db.commit()
    return {"experimento": svc.experiment_dict(exp), "version_modelo": svc.model_dict(mv)}


@router.post("/compare", status_code=201)
def compare(body: CompareIn, request: Request, db: Session = Depends(get_db), user: Usuario = Researcher):
    base = {k: v for k, v in body.config.items() if k not in ("algorithm", "params")}
    out = svc.compare(db, request.app.state.storage, user, _dv(db, body.dataset_version_id), base, body.algoritmos,
                      body.parametros)
    audit(db, user, "comparar_modelos", f"grupo:{out['grupo']}", {"algoritmos": body.algoritmos}, request)
    db.commit()
    table = pd.DataFrame(out["tabla"]).rename(columns={"nombre": "modelo"})
    out["grafico_rmse"] = _fig(plots.metric_comparison(table, "rmse"))
    out["grafico_r2"] = _fig(plots.metric_comparison(table, "r2"))
    return out


@router.get("")
def list_experiments(db: Session = Depends(get_db), _: Usuario = Researcher):
    return [svc.experiment_dict(e) for e in db.scalars(select(Experimento).order_by(Experimento.id.desc())).all()]


@router.get("/groups/{group}")
def group(group: str, db: Session = Depends(get_db), _: Usuario = Researcher):
    exps = db.scalars(select(Experimento).where(Experimento.grupo_comparacion == group)).all()
    if not exps:
        raise HTTPException(404, "Grupo de comparación no encontrado")
    rows = [{"experimento_id": e.id, "algoritmo": e.algoritmo, "modelo": e.resumen["nombre"],
             **{k: e.resumen.get(k) for k in ("rmse_cv_media", "rmse_cv_de", "r2_cv_media", "mae_test", "rmse_test",
                                              "r2_test", "rmse_entrenamiento")}} for e in exps]
    return clean_json({"tabla": rows, "seleccion": exps[0].resumen.get("seleccion_grupo"),
                       "grafico_rmse": _fig(plots.metric_comparison(pd.DataFrame(rows), "rmse"))})


@router.get("/{experiment_id}")
def get(experiment_id: int, db: Session = Depends(get_db), _: Usuario = Researcher):
    e = db.get(Experimento, experiment_id)
    if e is None:
        raise HTTPException(404, "Experimento no encontrado")
    return svc.experiment_dict(e, full=True)


@router.get("/{experiment_id}/plots")
def experiment_plots(experiment_id: int, db: Session = Depends(get_db), _: Usuario = Researcher):
    e = db.get(Experimento, experiment_id)
    if e is None:
        raise HTTPException(404, "Experimento no encontrado")
    p = pd.DataFrame(e.resumen["predicciones_prueba"])
    labels = p["municipio"] if "municipio" in p else None
    imp = pd.DataFrame(e.resumen["importancia_permutacion_test"])
    return {
        "real_vs_predicho": _fig(plots.predicted_vs_actual(p.real, p.predicho, labels)),
        "residuos": _fig(plots.residuals_plot(p.real, p.predicho, labels)),
        "histograma_residuos": _fig(plots.residual_histogram(p.real, p.predicho)),
        "importancia": _fig(plots.feature_importance_bar(imp, title="Importancia por permutación (prueba)")),
    }
