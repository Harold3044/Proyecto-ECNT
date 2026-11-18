"""Aplicación FastAPI: fábrica, errores, arranque y registro de operaciones.

Ejecutar:  uvicorn ecnt_api.main:app --reload
Documentación interactiva: http://localhost:8000/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

import ecnt_core
from ecnt_api.config import Settings, get_settings
from ecnt_api.db import Base, get_db, make_engine, make_sessionmaker
from ecnt_api.orm import Auditoria, Usuario
from ecnt_api.routers import alerts, auth, catalog, datasets, experiments, models, territories
from ecnt_api.security import ADMIN, hash_password, require_roles
from ecnt_api.services.alerts import AlertError, seed_rules
from ecnt_api.services.datasets import DatasetValidationError
from ecnt_api.services.modeling import ModelStateError
from ecnt_api.utils import Storage, clean_json
from ecnt_core.cleaning import CleaningError
from ecnt_core.experiment import ExperimentError
from ecnt_core.io import DataFileError
from ecnt_core.models import ModelConfigError
from ecnt_core.registry import ModelBundleError
from ecnt_core.splitting import SplitError

log = logging.getLogger("ecnt_api")


def bootstrap(SessionLocal, settings: Settings) -> None:
    """Crea los usuarios iniciales (solo si no existe ninguno) y las reglas de alerta por defecto."""
    with SessionLocal() as db:
        if db.scalars(select(Usuario)).first() is None:
            for email, pwd, rol, nombre in (
                (settings.bootstrap_admin_email, settings.bootstrap_admin_password, "admin", "Administrador"),
                (settings.bootstrap_investigador_email, settings.bootstrap_investigador_password, "investigador",
                 "Investigador"),
                (settings.bootstrap_eps_email, settings.bootstrap_eps_password, "eps", "Usuario EPS"),
            ):
                db.add(Usuario(email=email.lower(), nombre=nombre, rol=rol, password_hash=hash_password(pwd)))
        seed_rules(db)
        db.commit()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = make_engine(settings.database_url)
    SessionLocal = make_sessionmaker(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(engine)
        bootstrap(SessionLocal, settings)
        yield
        engine.dispose()

    app = FastAPI(title="Plataforma ECNT — API", version=ecnt_core.__version__, lifespan=lifespan,
                  description="API REST de la plataforma de IA para estimar indicadores territoriales de ECNT "
                              "asociados a determinantes sociales en el Caribe colombiano. Grupo 05.")
    app.state.settings = settings
    app.state.SessionLocal = SessionLocal
    app.state.storage = Storage(settings.storage_dir)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(DatasetValidationError)
    async def _dataset_invalid(_: Request, exc: DatasetValidationError):
        return JSONResponse(status_code=422, content={"detail": str(exc), "validacion": exc.report})

    @app.exception_handler(ValueError)
    async def _value_error(_: Request, exc: ValueError):
        known = (DataFileError, CleaningError, SplitError, ModelConfigError, ExperimentError, ModelStateError,
                 AlertError, ModelBundleError)
        if isinstance(exc, known):
            return JSONResponse(status_code=400, content={"detail": str(exc)})
        log.exception("Error de valor no controlado")
        return JSONResponse(status_code=400, content={"detail": f"Solicitud inválida: {exc}"})

    @app.get("/health", tags=["sistema"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": ecnt_core.__version__}

    @app.get("/audit", tags=["sistema"], dependencies=[Depends(require_roles(*ADMIN))])
    def audit_log(limit: int = 200, accion: str | None = None, db: Session = Depends(get_db)):
        q = select(Auditoria).order_by(Auditoria.id.desc()).limit(max(1, min(limit, 1000)))
        if accion:
            q = q.where(Auditoria.accion == accion)
        return clean_json([{"id": a.id, "usuario": a.usuario_email, "accion": a.accion, "recurso": a.recurso,
                            "detalle": a.detalle, "ip": a.ip, "fecha": a.creado} for a in db.scalars(q).all()])

    for r in (auth, catalog, datasets, experiments, models, territories, alerts):
        app.include_router(r.router)
    return app


app = create_app()
