"""Reglas de alerta (admin) y gestión/seguimiento de alertas (todos los roles)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ecnt_api.db import get_db
from ecnt_api.orm import Alerta, ReglaAlerta, Usuario
from ecnt_api.security import ADMIN, ANY, require_roles
from ecnt_api.services import alerts as svc
from ecnt_api.services.modeling import published_model
from ecnt_api.utils import audit

router = APIRouter(tags=["alertas"])
AnyUser = Depends(require_roles(*ANY))
Admin = Depends(require_roles(*ADMIN))


class RuleIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=200)
    tipo: str
    parametros: dict[str, Any] = Field(default_factory=dict)
    prioridad: str = "media"
    justificacion: str = Field(min_length=20, description="Justificación metodológica obligatoria")
    activa: bool = True


class RuleUpdate(BaseModel):
    nombre: str | None = None
    parametros: dict[str, Any] | None = None
    prioridad: str | None = None
    justificacion: str | None = None
    activa: bool | None = None


class AlertUpdate(BaseModel):
    estado: str | None = None
    prioridad: str | None = None
    responsable: str | None = Field(default=None, max_length=200)
    observacion: str | None = Field(default=None, max_length=2000)


@router.get("/alert-rules")
def rules(db: Session = Depends(get_db), _: Usuario = AnyUser):
    return [svc.rule_dict(r) for r in db.scalars(select(ReglaAlerta).order_by(ReglaAlerta.id)).all()]


@router.post("/alert-rules", status_code=201)
def create_rule(body: RuleIn, request: Request, db: Session = Depends(get_db), user: Usuario = Admin):
    svc.validate_rule(body.tipo, body.parametros, body.prioridad)
    r = ReglaAlerta(**body.model_dump())
    db.add(r)
    db.flush()
    audit(db, user, "crear_regla_alerta", f"regla:{r.id}", body.model_dump(), request)
    db.commit()
    return svc.rule_dict(r)


@router.patch("/alert-rules/{rule_id}")
def update_rule(rule_id: int, body: RuleUpdate, request: Request, db: Session = Depends(get_db),
                user: Usuario = Admin):
    r = db.get(ReglaAlerta, rule_id)
    if r is None:
        raise HTTPException(404, "Regla no encontrada")
    changes = body.model_dump(exclude_none=True)
    svc.validate_rule(r.tipo, changes.get("parametros", r.parametros), changes.get("prioridad", r.prioridad))
    for k, v in changes.items():
        setattr(r, k, v)
    audit(db, user, "actualizar_regla_alerta", f"regla:{r.id}", changes, request)
    db.commit()
    return svc.rule_dict(r)


@router.post("/alerts/generate")
def generate(request: Request, db: Session = Depends(get_db), user: Usuario = Admin):
    mv = published_model(db)
    if mv is None:
        raise HTTPException(404, "No hay un modelo publicado")
    out = svc.generate(db, mv, user)
    audit(db, user, "generar_alertas", f"modelo:{mv.id}", out, request)
    db.commit()
    return out


@router.get("/alerts")
def list_alerts(estado: str | None = None, prioridad: str | None = None, departamento: str | None = None,
                divipola: str | None = None, db: Session = Depends(get_db), _: Usuario = AnyUser):
    q = select(Alerta).order_by(Alerta.id.desc())
    if estado:
        q = q.where(Alerta.estado == estado)
    if prioridad:
        q = q.where(Alerta.prioridad == prioridad)
    if departamento:
        q = q.where(Alerta.departamento == departamento)
    if divipola:
        q = q.where(Alerta.divipola == divipola)
    return [svc.alert_dict(a) for a in db.scalars(q).all()]


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: int, db: Session = Depends(get_db), _: Usuario = AnyUser):
    a = db.get(Alerta, alert_id)
    if a is None:
        raise HTTPException(404, "Alerta no encontrada")
    return svc.alert_dict(a, events=True)


@router.patch("/alerts/{alert_id}")
def update_alert(alert_id: int, body: AlertUpdate, request: Request, db: Session = Depends(get_db),
                 user: Usuario = AnyUser):
    a = db.get(Alerta, alert_id)
    if a is None:
        raise HTTPException(404, "Alerta no encontrada")
    svc.update(db, a, user, **body.model_dump())
    audit(db, user, "actualizar_alerta", f"alerta:{a.id}", body.model_dump(exclude_none=True), request)
    db.commit()
    return svc.alert_dict(a, events=True)
