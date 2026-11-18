"""Consulta territorial y dashboard (todos los roles; datos agregados)."""

from __future__ import annotations

import io

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ecnt_api.db import get_db
from ecnt_api.orm import Usuario
from ecnt_api.security import ANY, require_roles
from ecnt_api.services import territories as svc
from ecnt_api.services.modeling import published_model
from ecnt_api.utils import audit

router = APIRouter(tags=["territorios"])
AnyUser = Depends(require_roles(*ANY))


def _published(db: Session):
    mv = published_model(db)
    if mv is None:
        raise HTTPException(404, "Aún no hay un modelo publicado. El administrador debe aprobar y publicar uno.")
    return mv


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db), _: Usuario = AnyUser):
    return svc.dashboard(db, request.app.state.storage, _published(db))


@router.get("/territories")
def territories(departamento: str | None = None, nivel: str | None = None, db: Session = Depends(get_db),
                _: Usuario = AnyUser):
    return svc.list_territories(db, _published(db), departamento, nivel)


@router.get("/territories/compare")
def compare(ids: list[str] = Query(..., min_length=2, max_length=20), db: Session = Depends(get_db),
            _: Usuario = AnyUser):
    return svc.compare_territories(db, _published(db), ids)


@router.get("/territories/export")
def export(request: Request, departamento: str | None = None, db: Session = Depends(get_db),
           user: Usuario = AnyUser):
    rows = svc.list_territories(db, _published(db), departamento)
    buf = io.StringIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    audit(db, user, "exportar_informe", "territorios", {"departamento": departamento}, request)
    db.commit()
    return StreamingResponse(iter(["﻿" + buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=informe_territorial.csv"})


@router.get("/territories/{divipola}")
def detail(divipola: str, request: Request, db: Session = Depends(get_db), user: Usuario = AnyUser):
    out = svc.territory_detail(db, request.app.state.storage, _published(db), divipola, user.rol,
                               request.app.state.settings.min_cell_size)
    if out is None:
        raise HTTPException(404, "Territorio no encontrado en el modelo publicado")
    return out
