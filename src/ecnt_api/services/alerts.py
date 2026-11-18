"""Sistema de alertas poblacionales: reglas configurables, generación, estados e historial.

Las alertas apoyan la planificación de acciones de salud pública. NO son diagnósticos.
"""

from __future__ import annotations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ecnt_api.orm import (
    ALERT_STATES,
    ALERT_TRANSITIONS,
    PRIORITIES,
    Alerta,
    AlertaEvento,
    Prediccion,
    ReglaAlerta,
    Usuario,
    VersionModelo,
)
from ecnt_api.utils import clean_json

RULE_TYPES = {
    "percentil_prediccion": "Mortalidad esperada (predicha) en el percentil superior del territorio",
    "exceso_observado": "Mortalidad observada por encima del límite superior del intervalo del 90 %",
    "posible_subregistro": "Mortalidad observada por debajo del límite inferior del intervalo del 90 %",
    "umbral_absoluto": "Mortalidad esperada por encima de un umbral fijo (por 100.000 hab.)",
}
CLOSED = {"cerrada", "descartada"}

DEFAULT_RULES = [
    dict(nombre="Mortalidad esperada alta (quintil superior)", tipo="percentil_prediccion",
         parametros={"percentil": 80}, prioridad="media",
         justificacion="Prioriza territorios cuyas condiciones sociales y demográficas se asocian con la mayor "
                       "mortalidad por ECNT esperada. Usa la predicción fuera de muestra del modelo publicado."),
    dict(nombre="Exceso de mortalidad observada", tipo="exceso_observado", parametros={}, prioridad="alta",
         justificacion="La mortalidad registrada supera lo esperado más allá del intervalo de predicción del 90 %: "
                       "situación inusual que amerita revisión epidemiológica."),
    dict(nombre="Posible subregistro de mortalidad", tipo="posible_subregistro", parametros={}, prioridad="media",
         justificacion="La mortalidad registrada es inferior a lo esperado más allá del intervalo del 90 %. En "
                       "territorios rurales dispersos suele reflejar subregistro o baja certificación médica, "
                       "no menor riesgo: amerita verificar la calidad del registro y el acceso a servicios."),
    dict(nombre="Umbral fijo de mortalidad esperada", tipo="umbral_absoluto", parametros={"umbral": 250},
         prioridad="alta", activa=False,
         justificacion="Umbral configurable por la EPS según sus metas; desactivado por defecto."),
]


class AlertError(ValueError):
    pass


def seed_rules(db: Session) -> None:
    if db.scalars(select(ReglaAlerta)).first() is None:
        for r in DEFAULT_RULES:
            db.add(ReglaAlerta(**r))


def validate_rule(tipo: str, parametros: dict, prioridad: str) -> None:
    if tipo not in RULE_TYPES:
        raise AlertError(f"Tipo de regla desconocido. Opciones: {list(RULE_TYPES)}")
    if prioridad not in PRIORITIES:
        raise AlertError(f"Prioridad inválida. Opciones: {PRIORITIES}")
    if tipo == "percentil_prediccion" and not 50 <= float(parametros.get("percentil", 80)) < 100:
        raise AlertError("El percentil debe estar entre 50 y 99")
    if tipo == "umbral_absoluto" and float(parametros.get("umbral", -1)) <= 0:
        raise AlertError("El umbral debe ser positivo")


def _matches(rule: ReglaAlerta, preds: list[Prediccion]) -> list[tuple[Prediccion, str, dict]]:
    out = []
    if rule.tipo == "percentil_prediccion":
        p = float(rule.parametros.get("percentil", 80))
        cut = float(np.percentile([x.predicho for x in preds], p))
        for x in preds:
            if x.predicho >= cut:
                out.append((x, f"Mortalidad esperada {x.predicho:.1f} ≥ percentil {p:.0f} ({cut:.1f})",
                            {"predicho": x.predicho, "corte": cut, "percentil": p}))
    elif rule.tipo == "umbral_absoluto":
        u = float(rule.parametros["umbral"])
        for x in preds:
            if x.predicho >= u:
                out.append((x, f"Mortalidad esperada {x.predicho:.1f} ≥ umbral {u:.0f}", {"predicho": x.predicho,
                                                                                         "umbral": u}))
    elif rule.tipo in ("exceso_observado", "posible_subregistro"):
        for x in preds:
            if x.observado is None:
                continue
            if rule.tipo == "exceso_observado" and x.observado > x.lim_sup:
                out.append((x, f"Observado {x.observado:.1f} > límite superior {x.lim_sup:.1f} (esperado "
                               f"{x.predicho:.1f})", {"observado": x.observado, "esperado": x.predicho,
                                                      "lim_sup": x.lim_sup}))
            if rule.tipo == "posible_subregistro" and x.observado < x.lim_inf:
                out.append((x, f"Observado {x.observado:.1f} < límite inferior {x.lim_inf:.1f} (esperado "
                               f"{x.predicho:.1f})", {"observado": x.observado, "esperado": x.predicho,
                                                      "lim_inf": x.lim_inf}))
    return out


def generate(db: Session, mv: VersionModelo, user: Usuario | None) -> dict:
    preds = db.scalars(select(Prediccion).where(Prediccion.version_modelo_id == mv.id)).all()
    if not preds:
        raise AlertError("El modelo no tiene predicciones territoriales publicadas")
    rules = db.scalars(select(ReglaAlerta).where(ReglaAlerta.activa.is_(True))).all()
    open_keys = {(a.regla_id, a.divipola, a.version_modelo_id) for a in db.scalars(
        select(Alerta).where(Alerta.estado.not_in(CLOSED))).all()}
    created = 0
    for rule in rules:
        for p, detalle, evid in _matches(rule, preds):
            if (rule.id, p.divipola, mv.id) in open_keys:
                continue
            a = Alerta(regla_id=rule.id, version_modelo_id=mv.id, divipola=p.divipola, municipio=p.municipio,
                       departamento=p.departamento, periodo=p.periodo, titulo=f"{rule.nombre} — {p.municipio}",
                       detalle=detalle, evidencia=clean_json(evid), prioridad=rule.prioridad)
            a.eventos.append(AlertaEvento(usuario_id=user.id if user else None, tipo="creacion",
                                          valor_nuevo="nueva", observacion=f"Generada por la regla '{rule.nombre}'"))
            db.add(a)
            open_keys.add((rule.id, p.divipola, mv.id))
            created += 1
    db.flush()
    return {"creadas": created, "reglas_evaluadas": len(rules), "territorios": len(preds)}


def update(db: Session, alert: Alerta, user: Usuario, estado: str | None = None, prioridad: str | None = None,
           responsable: str | None = None, observacion: str | None = None) -> Alerta:
    changed = False
    if estado is not None and estado != alert.estado:
        if estado not in ALERT_STATES:
            raise AlertError(f"Estado inválido. Opciones: {ALERT_STATES}")
        if estado not in ALERT_TRANSITIONS[alert.estado]:
            raise AlertError(f"Transición no permitida: {alert.estado} → {estado}. "
                             f"Permitidas: {sorted(ALERT_TRANSITIONS[alert.estado])}")
        if estado in CLOSED and not observacion:
            raise AlertError("Cerrar o descartar una alerta requiere una observación")
        if estado == "asignada" and not (responsable or alert.responsable):
            raise AlertError("Para asignar una alerta indique un responsable")
        alert.eventos.append(AlertaEvento(usuario_id=user.id, tipo="estado", valor_anterior=alert.estado,
                                          valor_nuevo=estado))
        alert.estado = estado
        changed = True
    if prioridad is not None and prioridad != alert.prioridad:
        if prioridad not in PRIORITIES:
            raise AlertError(f"Prioridad inválida. Opciones: {PRIORITIES}")
        alert.eventos.append(AlertaEvento(usuario_id=user.id, tipo="prioridad", valor_anterior=alert.prioridad,
                                          valor_nuevo=prioridad))
        alert.prioridad = prioridad
        changed = True
    if responsable is not None and responsable != alert.responsable:
        alert.eventos.append(AlertaEvento(usuario_id=user.id, tipo="responsable", valor_anterior=alert.responsable,
                                          valor_nuevo=responsable))
        alert.responsable = responsable
        changed = True
    if observacion:
        alert.eventos.append(AlertaEvento(usuario_id=user.id, tipo="observacion", observacion=observacion))
        changed = True
    if not changed:
        raise AlertError("No se indicó ningún cambio")
    db.flush()
    return alert


def rule_dict(r: ReglaAlerta) -> dict:
    return clean_json({"id": r.id, "nombre": r.nombre, "tipo": r.tipo, "descripcion_tipo": RULE_TYPES.get(r.tipo),
                       "parametros": r.parametros, "prioridad": r.prioridad, "justificacion": r.justificacion,
                       "activa": r.activa})


def alert_dict(a: Alerta, events: bool = False) -> dict:
    d = {"id": a.id, "regla_id": a.regla_id, "regla": a.regla.nombre if a.regla else None,
         "version_modelo_id": a.version_modelo_id, "divipola": a.divipola, "municipio": a.municipio,
         "departamento": a.departamento, "periodo": a.periodo, "titulo": a.titulo, "detalle": a.detalle,
         "evidencia": a.evidencia, "prioridad": a.prioridad, "estado": a.estado, "responsable": a.responsable,
         "creado": a.creado, "actualizado": a.actualizado,
         "transiciones_permitidas": sorted(ALERT_TRANSITIONS[a.estado])}
    if events:
        d["historial"] = [{"id": e.id, "tipo": e.tipo, "valor_anterior": e.valor_anterior,
                           "valor_nuevo": e.valor_nuevo, "observacion": e.observacion, "usuario_id": e.usuario_id,
                           "creado": e.creado} for e in a.eventos]
    return clean_json(d)
