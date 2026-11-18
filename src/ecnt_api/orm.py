"""Modelo de datos persistente."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ecnt_api.db import Base

ROLES = ("admin", "investigador", "eps")


def now() -> datetime:
    return datetime.now(UTC)


class Usuario(Base):
    __tablename__ = "usuario"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    rol: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Dataset(Base):
    __tablename__ = "dataset"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(Text, default="")
    fuente: Mapped[str] = mapped_column(String(300), default="")
    origen: Mapped[str] = mapped_column(String(20))  # "archivo" | "formulario"
    rol: Mapped[str | None] = mapped_column(String(30), nullable=True)  # modelado | panel | externo
    es_sintetico: Mapped[bool] = mapped_column(Boolean, default=False)
    archivo_original: Mapped[str | None] = mapped_column(String(300), nullable=True)
    sha256_original: Mapped[str | None] = mapped_column(String(64), nullable=True)
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    versiones: Mapped[list[DatasetVersion]] = relationship(back_populates="dataset", order_by="DatasetVersion.numero")


class DatasetVersion(Base):
    __tablename__ = "dataset_version"
    __table_args__ = (UniqueConstraint("dataset_id", "numero"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("dataset.id"))
    numero: Mapped[int] = mapped_column(Integer)
    padre_id: Mapped[int | None] = mapped_column(ForeignKey("dataset_version.id"), nullable=True)
    descripcion: Mapped[str] = mapped_column(Text, default="")
    operaciones: Mapped[list] = mapped_column(JSON, default=list)  # linaje
    ruta: Mapped[str] = mapped_column(String(300))
    filas: Mapped[int] = mapped_column(Integer)
    columnas: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    validacion: Mapped[dict] = mapped_column(JSON, default=dict)
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    dataset: Mapped[Dataset] = relationship(back_populates="versiones")


class Experimento(Base):
    __tablename__ = "experimento"
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_version_id: Mapped[int] = mapped_column(ForeignKey("dataset_version.id"))
    grupo_comparacion: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    algoritmo: Mapped[str] = mapped_column(String(40))
    objetivo: Mapped[str] = mapped_column(String(100))
    config: Mapped[dict] = mapped_column(JSON)
    resumen: Mapped[dict] = mapped_column(JSON)
    rmse_cv: Mapped[float | None] = mapped_column(Float, nullable=True)
    rmse_test: Mapped[float | None] = mapped_column(Float, nullable=True)
    r2_test: Mapped[float | None] = mapped_column(Float, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="completado")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_por: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


MODEL_STATES = ("evaluado", "aprobado", "publicado", "retirado")


class VersionModelo(Base):
    __tablename__ = "version_modelo"
    id: Mapped[int] = mapped_column(primary_key=True)
    experimento_id: Mapped[int] = mapped_column(ForeignKey("experimento.id"), unique=True)
    nombre: Mapped[str] = mapped_column(String(200))
    algoritmo: Mapped[str] = mapped_column(String(40))
    objetivo: Mapped[str] = mapped_column(String(100))
    ruta: Mapped[str] = mapped_column(String(300))
    sha256: Mapped[str] = mapped_column(String(64))
    estado: Mapped[str] = mapped_column(String(20), default="evaluado")
    aprobado_por: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    aprobado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nota_aprobacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    publicado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    experimento: Mapped[Experimento] = relationship()


class Prediccion(Base):
    """Predicciones territoriales del modelo publicado (fuera de muestra) que consume la EPS."""
    __tablename__ = "prediccion"
    __table_args__ = (UniqueConstraint("version_modelo_id", "divipola", "periodo"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    version_modelo_id: Mapped[int] = mapped_column(ForeignKey("version_modelo.id"), index=True)
    divipola: Mapped[str] = mapped_column(String(5), index=True)
    municipio: Mapped[str] = mapped_column(String(200), default="")
    departamento: Mapped[str] = mapped_column(String(200), default="")
    periodo: Mapped[str] = mapped_column(String(20), default="")
    poblacion: Mapped[float | None] = mapped_column(Float, nullable=True)
    observado: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicho: Mapped[float] = mapped_column(Float)
    lim_inf: Mapped[float] = mapped_column(Float)
    lim_sup: Mapped[float] = mapped_column(Float)
    nivel: Mapped[str] = mapped_column(String(20))  # muy bajo … muy alto (quintiles)
    tipo: Mapped[str] = mapped_column(String(30), default="fuera_de_muestra")
    determinantes: Mapped[dict] = mapped_column(JSON, default=dict)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ReglaAlerta(Base):
    __tablename__ = "regla_alerta"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    tipo: Mapped[str] = mapped_column(String(40))  # percentil_prediccion | exceso_observado | ...
    parametros: Mapped[dict] = mapped_column(JSON, default=dict)
    prioridad: Mapped[str] = mapped_column(String(10), default="media")
    justificacion: Mapped[str] = mapped_column(Text)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


ALERT_STATES = ("nueva", "en_revision", "asignada", "en_seguimiento", "cerrada", "descartada")
ALERT_TRANSITIONS = {
    "nueva": {"en_revision", "asignada", "descartada"},
    "en_revision": {"asignada", "en_seguimiento", "cerrada", "descartada"},
    "asignada": {"en_seguimiento", "en_revision", "cerrada", "descartada"},
    "en_seguimiento": {"cerrada", "en_revision"},
    "cerrada": {"en_revision"},  # reabrir
    "descartada": {"en_revision"},
}
PRIORITIES = ("alta", "media", "baja")


class Alerta(Base):
    __tablename__ = "alerta"
    id: Mapped[int] = mapped_column(primary_key=True)
    regla_id: Mapped[int] = mapped_column(ForeignKey("regla_alerta.id"))
    version_modelo_id: Mapped[int] = mapped_column(ForeignKey("version_modelo.id"))
    divipola: Mapped[str] = mapped_column(String(5), index=True)
    municipio: Mapped[str] = mapped_column(String(200))
    departamento: Mapped[str] = mapped_column(String(200))
    periodo: Mapped[str] = mapped_column(String(20))
    titulo: Mapped[str] = mapped_column(String(300))
    detalle: Mapped[str] = mapped_column(Text)
    evidencia: Mapped[dict] = mapped_column(JSON, default=dict)
    prioridad: Mapped[str] = mapped_column(String(10))
    estado: Mapped[str] = mapped_column(String(20), default="nueva")
    responsable: Mapped[str | None] = mapped_column(String(200), nullable=True)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    actualizado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    regla: Mapped[ReglaAlerta] = relationship()
    eventos: Mapped[list[AlertaEvento]] = relationship(back_populates="alerta", order_by="AlertaEvento.id")


class AlertaEvento(Base):
    __tablename__ = "alerta_evento"
    id: Mapped[int] = mapped_column(primary_key=True)
    alerta_id: Mapped[int] = mapped_column(ForeignKey("alerta.id"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    tipo: Mapped[str] = mapped_column(String(30))  # creacion | estado | prioridad | responsable | observacion
    valor_anterior: Mapped[str | None] = mapped_column(String(300), nullable=True)
    valor_nuevo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    observacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    alerta: Mapped[Alerta] = relationship(back_populates="eventos")


class Auditoria(Base):
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    usuario_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    accion: Mapped[str] = mapped_column(String(60), index=True)
    recurso: Mapped[str] = mapped_column(String(100))
    detalle: Mapped[dict] = mapped_column(JSON, default=dict)
    ip: Mapped[str | None] = mapped_column(String(60), nullable=True)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
