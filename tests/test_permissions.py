"""Matriz de permisos: cada endpoint protegido se prueba con los tres roles y sin sesión.

Un rol NO permitido debe recibir 403; sin token, 401. Un rol permitido nunca debe recibir 401/403
(puede recibir 404/400/422 porque se usan identificadores inexistentes a propósito).
"""

import jwt
import pytest
from fastapi.testclient import TestClient

from ecnt_api.config import Settings
from ecnt_api.main import create_app

SECRET = "clave-permisos-suficientemente-larga-para-hs256-0123456789"
ADMIN, RES, ALL = {"admin"}, {"admin", "investigador"}, {"admin", "investigador", "eps"}
ENDPOINTS = [
    ("GET", "/auth/me", ALL), ("GET", "/users", ADMIN), ("POST", "/users", ADMIN), ("PATCH", "/users/999", ADMIN),
    ("GET", "/audit", ADMIN), ("GET", "/catalog/variables", ALL), ("GET", "/catalog/algorithms", ALL),
    ("GET", "/datasets", RES), ("GET", "/datasets/999", RES), ("POST", "/datasets/form", RES),
    ("GET", "/datasets/versions/999", RES), ("GET", "/datasets/versions/999/rows", RES),
    ("GET", "/datasets/versions/999/download", RES), ("GET", "/datasets/versions/999/eda", RES),
    ("POST", "/datasets/versions/999/clean", RES), ("POST", "/datasets/versions/999/features", RES),
    ("POST", "/datasets/versions/999/records", RES),
    ("GET", "/experiments", RES), ("POST", "/experiments", RES), ("POST", "/experiments/compare", RES),
    ("GET", "/experiments/999", RES), ("GET", "/experiments/999/plots", RES),
    ("GET", "/models", RES), ("GET", "/models/999", RES), ("GET", "/models/published", ALL),
    ("POST", "/models/999/approve", ADMIN), ("POST", "/models/999/publish", ADMIN),
    ("POST", "/models/999/retire", ADMIN), ("POST", "/models/999/predict-version/1", RES),
    ("GET", "/dashboard", ALL), ("GET", "/territories", ALL), ("GET", "/territories/08001", ALL),
    ("GET", "/territories/export", ALL),
    ("GET", "/alert-rules", ALL), ("POST", "/alert-rules", ADMIN), ("PATCH", "/alert-rules/999", ADMIN),
    ("POST", "/alerts/generate", ADMIN), ("GET", "/alerts", ALL), ("GET", "/alerts/999", ALL),
    ("PATCH", "/alerts/999", ALL),
]
CREDS = {"admin": ("admin@ecnt.local", "Admin2026!"), "investigador": ("investigador@ecnt.local", "Inv2026!"),
         "eps": ("eps@ecnt.local", "Eps2026!")}


@pytest.fixture(scope="module")
def ctx(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("perm")
    s = Settings(database_url=f"sqlite:///{(tmp / 'p.db').as_posix()}", storage_dir=tmp / "st", jwt_secret=SECRET)
    with TestClient(create_app(s)) as c:
        tokens = {r: c.post("/auth/login", data={"username": e, "password": p}).json()["access_token"]
                  for r, (e, p) in CREDS.items()}
        yield c, tokens


@pytest.mark.parametrize("method,path,allowed", ENDPOINTS, ids=[f"{m} {p}" for m, p, _ in ENDPOINTS])
def test_matriz_de_permisos(ctx, method, path, allowed):
    c, tokens = ctx
    assert c.request(method, path).status_code == 401, "sin token debe ser 401"
    for rol, tok in tokens.items():
        code = c.request(method, path, headers={"Authorization": f"Bearer {tok}"}, json={}).status_code
        if rol in allowed:
            assert code not in (401, 403), f"{rol} debería tener acceso a {method} {path} (recibió {code})"
        else:
            assert code == 403, f"{rol} NO debería tener acceso a {method} {path} (recibió {code})"


def test_token_manipulado_o_vencido(ctx):
    c, tokens = ctx
    payload = jwt.decode(tokens["eps"], options={"verify_signature": False})
    forjado = jwt.encode({**payload, "rol": "admin", "sub": "1"}, "otra-clave-que-no-es-la-del-servidor-0123456789",
                         algorithm="HS256")
    assert c.get("/users", headers={"Authorization": f"Bearer {forjado}"}).status_code == 401
    vencido = jwt.encode({**payload, "exp": 1}, SECRET, algorithm="HS256")
    assert c.get("/auth/me", headers={"Authorization": f"Bearer {vencido}"}).status_code == 401


def test_rol_en_token_no_otorga_privilegios(ctx):
    """Aunque el token (firmado) dijera rol admin, el servidor usa el rol guardado en la base de datos."""
    c, tokens = ctx
    payload = jwt.decode(tokens["eps"], options={"verify_signature": False})
    elevado = jwt.encode({**payload, "rol": "admin"}, SECRET, algorithm="HS256")
    assert c.get("/users", headers={"Authorization": f"Bearer {elevado}"}).status_code == 403


def test_usuario_desactivado_pierde_acceso(ctx):
    c, tokens = ctx
    h = {"Authorization": f"Bearer {tokens['admin']}"}
    u = c.post("/users", headers=h, json={"email": "temp@eps.co", "nombre": "Temporal", "rol": "eps",
                                          "password": "ClaveTemporal1"}).json()
    tok = c.post("/auth/login", data={"username": "temp@eps.co", "password": "ClaveTemporal1"}).json()["access_token"]
    assert c.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 200
    c.patch(f"/users/{u['id']}", headers=h, json={"activo": False})
    assert c.get("/auth/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401
    assert c.post("/auth/login", data={"username": "temp@eps.co", "password": "ClaveTemporal1"}).status_code == 401


def test_admin_no_puede_desactivarse_a_si_mismo(ctx):
    c, tokens = ctx
    h = {"Authorization": f"Bearer {tokens['admin']}"}
    me = c.get("/auth/me", headers=h).json()
    assert c.patch(f"/users/{me['id']}", headers=h, json={"activo": False}).status_code == 400
