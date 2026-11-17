"""Pruebas básicas de que el entorno y los paquetes funcionan."""

from fastapi.testclient import TestClient

from ecnt_api.main import app


def test_health():
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_dependencias_criticas_importan():
    import pandas  # noqa: F401
    import plotly  # noqa: F401
    import sklearn  # noqa: F401
    import sqlalchemy  # noqa: F401
    import streamlit  # noqa: F401
