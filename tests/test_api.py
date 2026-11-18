"""Pruebas de integración de la API (BD y almacenamiento temporales, datos SINTÉTICOS)."""

import io

import pytest
from fastapi.testclient import TestClient

from ecnt_api.config import Settings
from ecnt_api.main import create_app
from tests.conftest import make_synthetic

FEATS = ["nbi_total", "comp_servicios_total", "pct_poblacion_resto", "pct_65_mas", "poblacion_2018"]
FAST = {"features": FEATS, "cv_repeats": 1}
USERS = {"admin": ("admin@ecnt.local", "Admin2026!"), "investigador": ("investigador@ecnt.local", "Inv2026!"),
         "eps": ("eps@ecnt.local", "Eps2026!")}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("api")
    settings = Settings(database_url=f"sqlite:///{(tmp / 't.db').as_posix()}", storage_dir=tmp / "storage",
                        jwt_secret="clave-de-prueba-suficientemente-larga-para-hs256-0123456789")
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture(scope="module")
def h(client):
    out = {}
    for rol, (email, pwd) in USERS.items():
        r = client.post("/auth/login", data={"username": email, "password": pwd})
        assert r.status_code == 200, r.text
        out[rol] = {"Authorization": f"Bearer {r.json()['access_token']}"}
    return out


def _csv(df) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


@pytest.fixture(scope="module")
def dataset(client, h):
    df = make_synthetic(150, seed=1)
    r = client.post("/datasets/upload", headers=h["investigador"],
                    files={"archivo": ("SINTETICO_caribe.csv", _csv(df), "text/csv")},
                    data={"nombre": "SINTÉTICO de prueba", "fuente": "generador de pruebas", "rol": "modelado",
                          "es_sintetico": "true"})
    assert r.status_code == 201, r.text
    return r.json()


# ------------------------------ Autenticación -------------------------------
def test_login_y_me(client, h):
    assert client.get("/auth/me", headers=h["eps"]).json()["rol"] == "eps"
    assert client.post("/auth/login", data={"username": "admin@ecnt.local", "password": "mala"}).status_code == 401
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer token-falso"}).status_code == 401


def test_permisos_por_rol(client, h):
    assert client.get("/datasets", headers=h["eps"]).status_code == 403
    assert client.post("/experiments", headers=h["eps"], json={"dataset_version_id": 1}).status_code == 403
    assert client.get("/users", headers=h["investigador"]).status_code == 403
    assert client.get("/audit", headers=h["eps"]).status_code == 403
    assert client.post("/alerts/generate", headers=h["investigador"]).status_code == 403
    assert client.get("/catalog/algorithms", headers=h["eps"]).status_code == 200


def test_admin_crea_usuario(client, h):
    r = client.post("/users", headers=h["admin"], json={"email": "nuevo@eps.co", "nombre": "Analista EPS",
                                                        "rol": "eps", "password": "ClaveSegura1"})
    assert r.status_code == 201
    assert client.post("/users", headers=h["admin"], json={"email": "nuevo@eps.co", "nombre": "x y", "rol": "eps",
                                                           "password": "ClaveSegura1"}).status_code == 409


# ------------------------------- Datasets -----------------------------------
def test_carga_masiva_y_rechazo_de_datos_personales(client, h, dataset):
    assert dataset["version"]["numero"] == 1 and dataset["version"]["filas"] == 150
    assert dataset["dataset"]["es_sintetico"] is True
    n_before = len(client.get("/datasets", headers=h["admin"]).json())
    bad = make_synthetic(20).assign(documento_paciente="123")
    r = client.post("/datasets/upload", headers=h["admin"], files={"archivo": ("x.csv", _csv(bad), "text/csv")},
                    data={"nombre": "malo"})
    assert r.status_code == 422 and any(i["code"] == "dato_personal" for i in r.json()["validacion"]["issues"])
    assert len(client.get("/datasets", headers=h["admin"]).json()) == n_before  # no se guardó nada
    r = client.post("/datasets/upload", headers=h["admin"], files={"archivo": ("x.txt", b"abc", "text/plain")},
                    data={"nombre": "malo"})
    assert r.status_code == 400


def test_formulario_y_versionado(client, h):
    rec = {"divipola": "20001", "municipio": "Territorio de prueba", "periodo": "2018-2019", "nbi_total": 30.5}
    r = client.post("/datasets/form", headers=h["investigador"], json={"nombre": "Formulario", "registros": [rec],
                                                                       "es_sintetico": True})
    assert r.status_code == 201
    v1 = r.json()["version"]
    r = client.post(f"/datasets/versions/{v1['id']}/records", headers=h["investigador"],
                    json={"registros": [{**rec, "divipola": "20011", "nbi_total": 41}]})
    assert r.status_code == 201 and r.json()["numero"] == 2 and r.json()["filas"] == 2
    r = client.post(f"/datasets/versions/{v1['id']}/records", headers=h["investigador"],
                    json={"registros": [{"divipola": "123"}]})
    assert r.status_code == 422  # DIVIPOLA inválido


def test_eda_limpieza_y_original_inmutable(client, h, dataset):
    vid = dataset["version"]["id"]
    e = client.get(f"/datasets/versions/{vid}/eda", headers=h["investigador"]).json()
    assert e["calidad"]["filas"] == 150 and any(d["variable"] == "nbi_total" for d in e["descriptivas"])
    assert "data" in client.get(f"/datasets/versions/{vid}/eda/plot", params={"kind": "histogram",
                                "column": "nbi_total"}, headers=h["investigador"]).json()
    c = client.get(f"/datasets/versions/{vid}/eda/correlation", params={"target": "tasa_mort_ecnt_std"},
                   headers=h["investigador"]).json()
    assert c["con_objetivo"][0]["variable"] == "pct_poblacion_resto"
    assert client.get(f"/datasets/versions/{vid}/eda/frequencies", params={"column": "departamento"},
                      headers=h["investigador"]).status_code == 200
    r = client.post(f"/datasets/versions/{vid}/clean", headers=h["investigador"],
                    json={"pasos": [{"op": "log1p", "columns": ["poblacion_2018"]}]})
    assert r.status_code == 201 and r.json()["numero"] == 2 and r.json()["operaciones"][0]["op"] == "log1p"
    orig = client.get(f"/datasets/versions/{vid}/rows", params={"limit": 5}, headers=h["investigador"]).json()
    assert "poblacion_2018_log" not in orig["columnas"]
    r = client.post(f"/datasets/versions/{vid}/clean", headers=h["investigador"], json={"pasos": [{"op": "zzz"}]})
    assert r.status_code == 400
    assert client.get(f"/datasets/versions/{vid}/download", headers=h["investigador"]).text.startswith("divipola")


def test_seleccion_de_variables_solo_entrenamiento(client, h, dataset):
    r = client.post(f"/datasets/versions/{dataset['version']['id']}/features", headers=h["investigador"],
                    json={"variables": FEATS, "proporcion": "75/25", "semilla": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["n_entrenamiento"] + body["n_prueba_excluida"] == 150 and body["n_entrenamiento"] < 150
    assert body["ranking"][0]["variable"] == "pct_poblacion_resto"


# ------------------------- Experimentos y modelos ---------------------------
@pytest.fixture(scope="module")
def comparison(client, h, dataset):
    r = client.post("/experiments/compare", headers=h["investigador"], json={
        "dataset_version_id": dataset["version"]["id"], "config": {**FAST, "ratio": "80/20", "seed": 5},
        "algoritmos": ["baseline", "linear", "random_forest"]})
    assert r.status_code == 201, r.text
    return r.json()


def test_comparacion_y_graficos(client, h, comparison):
    assert len(comparison["tabla"]) == 3 and comparison["seleccion"]["elegido"] == "linear"
    exp_id = comparison["tabla"][1]["experimento_id"]
    plots = client.get(f"/experiments/{exp_id}/plots", headers=h["investigador"]).json()
    assert set(plots) == {"real_vs_predicho", "residuos", "histograma_residuos", "importancia"}
    g = client.get(f"/experiments/groups/{comparison['grupo']}", headers=h["investigador"]).json()
    assert g["seleccion"]["elegido"] == "linear"
    bad = client.post("/experiments", headers=h["investigador"], json={
        "dataset_version_id": 1, "config": {"algorithm": "linear", "features": ["tasa_mort_ecnt_std"]}})
    assert bad.status_code == 400


def test_flujo_aprobacion_publicacion_y_eps(client, h, comparison):
    mid = next(t["version_modelo_id"] for t in comparison["tabla"] if t["algoritmo"] == "linear")
    base_id = next(t["version_modelo_id"] for t in comparison["tabla"] if t["algoritmo"] == "baseline")
    assert client.get("/dashboard", headers=h["eps"]).status_code == 404  # aún no hay modelo publicado
    assert client.post(f"/models/{mid}/publish", headers=h["admin"]).status_code == 400  # sin aprobar
    ok_note = {"justificacion": "Supera la línea base y cumple la regla de 1 EE."}
    assert client.post(f"/models/{mid}/approve", headers=h["investigador"], json=ok_note).status_code == 403
    assert client.post(f"/models/{mid}/approve", headers=h["admin"], json={"justificacion": "ok"}).status_code == 422
    assert client.post(f"/models/{base_id}/approve", headers=h["admin"], json=ok_note).status_code == 400
    r = client.post(f"/models/{mid}/approve", headers=h["admin"], json=ok_note)
    assert r.status_code == 200 and r.json()["estado"] == "aprobado"
    r = client.post(f"/models/{mid}/publish", headers=h["admin"])
    assert r.status_code == 200 and r.json()["predicciones"] == 150 and r.json()["alertas"]["creadas"] > 0

    d = client.get("/dashboard", headers=h["eps"]).json()
    assert d["total_territorios"] == 150 and "aviso" in d and len(d["distribucion_niveles"]) == 5
    terr = client.get("/territories", headers=h["eps"]).json()
    det = client.get(f"/territories/{terr[0]['divipola']}", headers=h["eps"]).json()
    assert det["lim_inf"] <= det["predicho"] <= det["lim_sup"] and det["tipo_prediccion"] == "fuera_de_muestra"
    assert len(det["determinantes"]) == len(FEATS)
    cmp_ = client.get("/territories/compare", params=[("ids", terr[0]["divipola"]), ("ids", terr[1]["divipola"])],
                      headers=h["eps"]).json()
    assert len(cmp_) == 2
    assert client.get("/territories/export", headers=h["eps"]).status_code == 200
    assert client.get("/territories/99999", headers=h["eps"]).status_code == 404
    assert client.get("/models/published", headers=h["eps"]).json()["id"] == mid

    # publicar otro modelo retira el anterior (nunca dos publicados para el mismo objetivo)
    rf = next(t["version_modelo_id"] for t in comparison["tabla"] if t["algoritmo"] == "random_forest")
    client.post(f"/models/{rf}/approve", headers=h["admin"], json=ok_note)
    r = client.post(f"/models/{rf}/publish", headers=h["admin"]).json()
    assert r["retirados"] == [mid]
    assert client.get("/models/published", headers=h["eps"]).json()["id"] == rf


def test_alertas_estados_e_historial(client, h, comparison):
    alerts = client.get("/alerts", headers=h["eps"]).json()
    assert alerts and all(a["estado"] == "nueva" for a in alerts)
    aid = alerts[0]["id"]
    p = lambda body: client.patch(f"/alerts/{aid}", headers=h["eps"], json=body)  # noqa: E731
    assert p({"estado": "en_seguimiento"}).status_code == 400  # transición no permitida desde 'nueva'
    assert p({"estado": "asignada"}).status_code == 400  # falta responsable
    assert p({"estado": "asignada", "responsable": "Coordinación de salud pública"}).status_code == 200
    assert p({"prioridad": "alta", "observacion": "Se programa visita técnica"}).status_code == 200
    assert p({"estado": "cerrada"}).status_code == 400  # cerrar exige observación
    r = p({"estado": "en_seguimiento"})
    assert r.status_code == 200
    hist = client.get(f"/alerts/{aid}", headers=h["eps"]).json()["historial"]
    assert [e["tipo"] for e in hist][:1] == ["creacion"] and len(hist) >= 5
    assert p({}).status_code == 400
    # regenerar no duplica alertas abiertas
    n = len(client.get("/alerts", headers=h["admin"]).json())
    assert client.post("/alerts/generate", headers=h["admin"]).json()["creadas"] == 0
    assert len(client.get("/alerts", headers=h["admin"]).json()) == n


def test_reglas_de_alerta_configurables(client, h):
    body = {"nombre": "Umbral EPS", "tipo": "umbral_absoluto", "parametros": {"umbral": 200}, "prioridad": "alta",
            "justificacion": "Meta institucional de la EPS para priorizar visitas."}
    assert client.post("/alert-rules", headers=h["eps"], json=body).status_code == 403
    r = client.post("/alert-rules", headers=h["admin"], json=body)
    assert r.status_code == 201
    bad = {**body, "parametros": {"umbral": -5}}
    assert client.post("/alert-rules", headers=h["admin"], json=bad).status_code == 400
    assert client.patch(f"/alert-rules/{r.json()['id']}", headers=h["admin"], json={"activa": False}).json()[
        "activa"] is False


def test_pruebas_con_datos_nuevos(client, h, comparison):
    mid = comparison["tabla"][1]["version_modelo_id"]
    nuevos = make_synthetic(40, seed=99)  # territorios independientes (otra semilla)
    r = client.post(f"/models/{mid}/predict", headers=h["investigador"],
                    files={"archivo": ("SINTETICO_nuevos.csv", _csv(nuevos), "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert body["n"] == 40 and body["metricas"]["r2"] > 0.5 and "cobertura_intervalo_90" in body
    r = client.post(f"/models/{mid}/predict", headers=h["investigador"],
                    files={"archivo": ("x.csv", _csv(nuevos.drop(columns=["nbi_total"])), "text/csv")})
    assert r.status_code == 400


def test_auditoria(client, h):
    log = client.get("/audit", headers=h["admin"]).json()
    acciones = {a["accion"] for a in log}
    assert {"login", "cargar_dataset", "comparar_modelos", "aprobar_modelo", "publicar_modelo",
            "actualizar_alerta"} <= acciones


def test_documentacion_openapi(client):
    spec = client.get("/openapi.json").json()
    assert {"/auth/login", "/datasets/upload", "/experiments/compare", "/models/{model_id}/publish",
            "/dashboard", "/alerts/{alert_id}"} <= set(spec["paths"])


def test_csv_con_bom_y_punto_y_coma(client, h):
    content = "﻿divipola;municipio;periodo;nbi_total\n08001;A;2018;20\n".encode()
    r = client.post("/datasets/validate", headers=h["admin"], files={"archivo": ("a.csv", io.BytesIO(content))})
    assert r.status_code == 200 and r.json()["columnas"][0] == "divipola"
