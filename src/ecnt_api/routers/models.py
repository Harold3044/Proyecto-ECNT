"""Gestión de versiones de modelo: consulta, comparación, aprobación, publicación y pruebas con datos nuevos."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ecnt_api.db import get_db
from ecnt_api.orm import DatasetVersion, Usuario, VersionModelo
from ecnt_api.security import ADMIN, ANY, RESEARCH, require_roles
from ecnt_api.services import alerts as alert_svc
from ecnt_api.services import modeling as svc
from ecnt_api.services.datasets import load_df
from ecnt_api.utils import audit
from ecnt_core.io import read_table

router = APIRouter(prefix="/models", tags=["modelos"])


class ApproveIn(BaseModel):
    justificacion: str = Field(min_length=10, max_length=2000)


def _mv(db: Session, model_id: int) -> VersionModelo:
    mv = db.get(VersionModelo, model_id)
    if mv is None:
        raise HTTPException(404, "Versión de modelo no encontrada")
    return mv


@router.get("", dependencies=[Depends(require_roles(*RESEARCH))])
def list_models(estado: str | None = None, db: Session = Depends(get_db)):
    q = select(VersionModelo).order_by(VersionModelo.id.desc())
    if estado:
        q = q.where(VersionModelo.estado == estado)
    return [svc.model_dict(m) for m in db.scalars(q).all()]


@router.get("/published")
def published(db: Session = Depends(get_db), _: Usuario = Depends(require_roles(*ANY))):
    mv = svc.published_model(db)
    if mv is None:
        raise HTTPException(404, "No hay un modelo publicado")
    d = svc.model_dict(mv)
    return {k: d[k] for k in ("id", "nombre", "algoritmo", "objetivo", "publicado_en", "metricas", "variables")}


@router.get("/compare", dependencies=[Depends(require_roles(*RESEARCH))])
def compare_versions(ids: list[int] = Query(...), db: Session = Depends(get_db)):
    return [svc.model_dict(_mv(db, i)) for i in ids]


@router.get("/{model_id}", dependencies=[Depends(require_roles(*RESEARCH))])
def get_model(model_id: int, db: Session = Depends(get_db)):
    return svc.model_dict(_mv(db, model_id), full=True)


@router.post("/{model_id}/approve")
def approve(model_id: int, body: ApproveIn, request: Request, db: Session = Depends(get_db),
            user: Usuario = Depends(require_roles(*ADMIN))):
    mv = svc.approve(db, _mv(db, model_id), user, body.justificacion)
    audit(db, user, "aprobar_modelo", f"modelo:{mv.id}", {"justificacion": body.justificacion}, request)
    db.commit()
    return svc.model_dict(mv)


@router.post("/{model_id}/publish")
def publish(model_id: int, request: Request, db: Session = Depends(get_db),
            user: Usuario = Depends(require_roles(*ADMIN))):
    mv = _mv(db, model_id)
    out = svc.publish(db, request.app.state.storage, mv, user)
    out["alertas"] = alert_svc.generate(db, mv, user)
    audit(db, user, "publicar_modelo", f"modelo:{mv.id}", out, request)
    db.commit()
    return out


@router.post("/{model_id}/retire")
def retire(model_id: int, request: Request, db: Session = Depends(get_db),
           user: Usuario = Depends(require_roles(*ADMIN))):
    mv = svc.retire(_mv(db, model_id))
    audit(db, user, "retirar_modelo", f"modelo:{mv.id}", request=request)
    db.commit()
    return svc.model_dict(mv)


@router.post("/{model_id}/predict")
async def predict_file(model_id: int, request: Request, archivo: UploadFile = File(...),
                       db: Session = Depends(get_db), user: Usuario = Depends(require_roles(*RESEARCH))):
    """Pruebas con datos nuevos: el archivo no se guarda; se aplican las transformaciones del modelo."""
    df = read_table(await archivo.read(), archivo.filename or "archivo.csv")
    out = svc.predict_new(request.app.state.storage, _mv(db, model_id), df)
    audit(db, user, "predecir_datos_nuevos", f"modelo:{model_id}", {"archivo": archivo.filename, "n": out["n"]},
          request)
    db.commit()
    return out


@router.post("/{model_id}/predict-version/{version_id}")
def predict_version(model_id: int, version_id: int, request: Request, db: Session = Depends(get_db),
                    user: Usuario = Depends(require_roles(*RESEARCH))):
    v = db.get(DatasetVersion, version_id)
    if v is None:
        raise HTTPException(404, "Versión de dataset no encontrada")
    storage = request.app.state.storage
    out = svc.predict_new(storage, _mv(db, model_id), load_df(storage, v))
    audit(db, user, "predecir_datos_nuevos", f"modelo:{model_id}", {"dataset_version": version_id}, request)
    db.commit()
    return out
