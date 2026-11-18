"""Motor y sesiones de base de datos (SQLite por defecto; PostgreSQL vía ECNT_DATABASE_URL)."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, future=True, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _fk(dbapi_conn, _):  # integridad referencial en SQLite
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
    return engine


def make_sessionmaker(engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db(request: Request) -> Iterator[Session]:
    db: Session = request.app.state.SessionLocal()
    try:
        yield db
    finally:
        db.close()
