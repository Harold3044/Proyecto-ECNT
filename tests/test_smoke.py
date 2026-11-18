"""Pruebas básicas de que el entorno y los paquetes funcionan."""

from fastapi.testclient import TestClient

from ecnt_api.config import Settings
from ecnt_api.main import create_app


def test_health(tmp_path):
    s = Settings(database_url=f"sqlite:///{(tmp_path / 'h.db').as_posix()}", storage_dir=tmp_path)
    with TestClient(create_app(s)) as c:
        r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_dependencias_criticas_importan():
    import pandas  # noqa: F401
    import plotly  # noqa: F401
    import sklearn  # noqa: F401
    import sqlalchemy  # noqa: F401
    import streamlit  # noqa: F401
