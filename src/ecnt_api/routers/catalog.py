"""Catálogos de referencia para construir formularios en las interfaces."""

from fastapi import APIRouter, Depends

from ecnt_api.orm import ALERT_STATES, ALERT_TRANSITIONS, PRIORITIES
from ecnt_api.security import ANY, require_roles
from ecnt_api.services.alerts import RULE_TYPES
from ecnt_core.cleaning import list_operations
from ecnt_core.models import algorithms_catalog
from ecnt_core.schemas import CANONICAL, DEFAULT_TARGET
from ecnt_core.splitting import ALLOWED_TEST_SIZES, STRATEGIES

router = APIRouter(prefix="/catalog", tags=["catálogos"], dependencies=[Depends(require_roles(*ANY))])


@router.get("/variables")
def variables():
    return {"objetivo_por_defecto": DEFAULT_TARGET, "variables": [s.to_dict() for s in CANONICAL.values()]}


@router.get("/algorithms")
def algorithms():
    return algorithms_catalog()


@router.get("/cleaning-operations")
def cleaning_operations():
    return list_operations()


@router.get("/split-options")
def split_options():
    return {"proporciones": list(ALLOWED_TEST_SIZES), "estrategias": list(STRATEGIES),
            "seleccion_variables": ["none", "ranking_top_k", "kbest"]}


@router.get("/alerts")
def alert_catalog():
    return {"tipos_regla": RULE_TYPES, "estados": ALERT_STATES, "prioridades": PRIORITIES,
            "transiciones": {k: sorted(v) for k, v in ALERT_TRANSITIONS.items()}}
