"""Prueba de extremo a extremo de las interfaces: API real (uvicorn) + cada vista de Admin y EPS.

Levanta la API en un puerto libre con BD temporal, carga datos SINTÉTICOS por HTTP, publica un modelo
y renderiza cada vista con ``streamlit.testing.v1.AppTest`` verificando que no haya excepciones.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests
from streamlit.testing.v1 import AppTest

from ecnt_client import ApiClient
from tests.conftest import make_synthetic

ROOT = Path(__file__).resolve().parents[1]
FEATS = ["nbi_total", "comp_servicios_total", "pct_poblacion_resto", "pct_65_mas", "poblacion_2018"]

ADMIN_VIEWS = [("sistema", "inicio"), ("datos", "gestion"), ("datos", "carga_masiva"), ("datos", "formulario"),
               ("analisis", "exploratorio"), ("analisis", "limpieza"), ("analisis", "variables"),
               ("modelos", "entrenamiento"), ("modelos", "comparacion"), ("modelos", "gestion"),
               ("modelos", "datos_nuevos"), ("sistema", "reglas_alerta"), ("sistema", "usuarios"),
               ("sistema", "auditoria")]
EPS_VIEWS = ["dashboard", "consulta", "analisis", "mapa", "alertas", "informes"]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def api_url(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("e2e")
    port = _free_port()
    env = {**os.environ, "ECNT_DATABASE_URL": f"sqlite:///{(tmp / 'e2e.db').as_posix()}",
           "ECNT_STORAGE_DIR": str(tmp / "storage"),
           "ECNT_JWT_SECRET": "clave-e2e-suficientemente-larga-para-hs256-0123456789abcdef"}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "ecnt_api.main:app", "--port", str(port)],
                            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            if requests.get(f"{url}/health", timeout=1).ok:
                break
        except requests.RequestException:
            time.sleep(0.5)
    else:
        proc.kill()
        pytest.fail("La API no arrancó")
    # Siembra por HTTP: dataset sintético → comparación → aprobación → publicación
    adm = ApiClient(url)
    adm.login("admin@ecnt.local", "Admin2026!")
    df = make_synthetic(120, seed=4)
    v = adm.upload("/datasets/upload", "SINTETICO.csv", df.to_csv(index=False).encode(),
                   {"nombre": "SINTÉTICO e2e", "rol": "modelado", "es_sintetico": "true"})["version"]
    cmp_ = adm.post("/experiments/compare", {"dataset_version_id": v["id"],
                                             "config": {"features": FEATS, "cv_repeats": 1},
                                             "algoritmos": ["baseline", "linear", "random_forest"]})
    mid = next(t["version_modelo_id"] for t in cmp_["tabla"] if t["algoritmo"] == cmp_["seleccion"]["elegido"])
    adm.post(f"/models/{mid}/approve", {"justificacion": "Prueba de extremo a extremo con datos sintéticos."})
    adm.post(f"/models/{mid}/publish")
    yield url
    proc.terminate()
    proc.wait(timeout=10)


def _session(url: str, email: str, pwd: str) -> tuple[ApiClient, dict]:
    c = ApiClient(url)
    data = c.login(email, pwd)
    return c, data["usuario"]


def _content(at: AppTest) -> int:
    """Cantidad de elementos con contenido (métricas, tablas, gráficos)."""
    return len(at.metric) + len(at.dataframe) + len(at.get("plotly_chart"))


def _run(script: str, client: ApiClient, user: dict) -> AppTest:
    at = AppTest.from_string(script, default_timeout=120)
    at.session_state["api"] = client
    at.session_state["usuario"] = user
    return at.run()


@pytest.mark.parametrize("module,view", ADMIN_VIEWS)
def test_vistas_admin(api_url, module, view):
    client, user = _session(api_url, "admin@ecnt.local", "Admin2026!")
    script = (f"import sys; sys.path.insert(0, r'{ROOT / 'apps' / 'admin'}')\n"
              f"from vistas import {module}\n{module}.{view}()\n")
    at = _run(script, client, user)
    assert not at.exception, [e.message for e in at.exception]
    assert not at.error, [e.value for e in at.error]


@pytest.mark.parametrize("view", EPS_VIEWS)
def test_vistas_eps(api_url, view):
    client, user = _session(api_url, "eps@ecnt.local", "Eps2026!")
    script = (f"import sys; sys.path.insert(0, r'{ROOT / 'apps' / 'eps'}')\n"
              f"import vistas_eps\nvistas_eps.{view}()\n")
    at = _run(script, client, user)
    assert not at.exception, [e.message for e in at.exception]
    assert not at.error, [e.value for e in at.error]


def test_login_eps_rechaza_rol_no_permitido(api_url):
    """La app EPS no admite al rol investigador; la app Admin no admite al rol EPS."""
    script = (f"import sys; sys.path.insert(0, r'{ROOT / 'src'}')\n"
              "from ecnt_client.ui import login_gate\n"
              f"login_gate('EPS', ('eps', 'admin'))\n")
    at = AppTest.from_string(script, default_timeout=60).run()
    at.text_input[0].input("investigador@ecnt.local")
    at.text_input[1].input("Inv2026!")
    at.text_input[2].input(api_url)
    at.button[0].click().run()
    assert any("no tiene acceso" in e.value for e in at.error)
    assert "api" not in at.session_state


def test_interaccion_entrenar_desde_admin(api_url):
    client, user = _session(api_url, "investigador@ecnt.local", "Inv2026!")
    script = (f"import sys; sys.path.insert(0, r'{ROOT / 'apps' / 'admin'}')\n"
              "from vistas import modelos\nmodelos.entrenamiento()\n")
    at = _run(script, client, user)
    n_before = len(client.get("/experiments"))
    next(s for s in at.slider if "Repeticiones" in s.label).set_value(1)
    at.run()
    next(b for b in at.button if "Entrenar" in b.label).click().run(timeout=300)
    assert not at.exception and not at.error, [e.value for e in at.error]
    assert any("Modelo recomendado" in s.value for s in at.success)
    assert len(client.get("/experiments")) == n_before + 5


def test_interaccion_seguimiento_alerta_eps(api_url):
    client, user = _session(api_url, "eps@ecnt.local", "Eps2026!")
    alert = next(a for a in client.get("/alerts") if a["estado"] == "nueva")
    script = (f"import sys; sys.path.insert(0, r'{ROOT / 'apps' / 'eps'}')\n"
              "import vistas_eps\nvistas_eps.alertas()\n")
    at = _run(script, client, user)
    next(s for s in at.selectbox if s.label == "Alerta").set_value(alert["id"]).run()
    next(s for s in at.selectbox if s.label == "Cambiar estado").set_value("asignada")
    next(t for t in at.text_input if t.label == "Responsable").input("Equipo de salud pública")
    next(t for t in at.text_area if t.label == "Observación").input("Se programa visita de verificación")
    next(b for b in at.button if "Registrar" in b.label).click().run()
    assert not at.exception and not at.error, [e.value for e in at.error]
    a = client.get(f"/alerts/{alert['id']}")
    assert a["estado"] == "asignada" and a["responsable"] == "Equipo de salud pública"
    assert {"estado", "responsable", "observacion"} <= {e["tipo"] for e in a["historial"]}
