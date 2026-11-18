"""Cliente HTTP de la API ECNT. Es el ÚNICO punto de contacto de las aplicaciones con el backend."""

from __future__ import annotations

import os
from typing import Any

import requests

# 127.0.0.1 y no "localhost": en Windows "localhost" intenta primero IPv6 (::1) y, como uvicorn escucha en
# IPv4, cada petición esperaba ~2 s antes de reintentar por IPv4 (medido en la prueba de rendimiento).
DEFAULT_URL = os.environ.get("ECNT_API_URL", "http://127.0.0.1:8000")


class ApiError(Exception):
    def __init__(self, status: int, detail: Any, validacion: dict | None = None):
        self.status = status
        self.detail = detail
        self.validacion = validacion
        super().__init__(self.message)

    @property
    def message(self) -> str:
        if self.status == 0:
            return f"No se pudo conectar con la API: {self.detail}"
        if isinstance(self.detail, list):  # errores de validación de FastAPI
            return "; ".join(f"{'.'.join(str(x) for x in e.get('loc', []))}: {e.get('msg')}" for e in self.detail)
        return str(self.detail)


class ApiClient:
    def __init__(self, base_url: str = DEFAULT_URL, token: str | None = None, timeout: float = 300):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _request(self, method: str, path: str, **kw) -> requests.Response:
        try:
            r = requests.request(method, f"{self.base_url}{path}", headers=self._headers(), timeout=self.timeout, **kw)
        except requests.RequestException as exc:
            raise ApiError(0, str(exc)) from exc
        if r.status_code >= 400:
            try:
                body = r.json()
                raise ApiError(r.status_code, body.get("detail", body), body.get("validacion"))
            except ValueError:
                raise ApiError(r.status_code, r.text) from None
        return r

    def login(self, email: str, password: str) -> dict:
        data = self._request("POST", "/auth/login", data={"username": email, "password": password}).json()
        self.token = data["access_token"]
        return data

    def get(self, path: str, **params) -> Any:
        return self._request("GET", path, params={k: v for k, v in params.items() if v is not None}).json()

    def post(self, path: str, json: Any = None) -> Any:
        return self._request("POST", path, json=json).json()

    def patch(self, path: str, json: Any) -> Any:
        return self._request("PATCH", path, json=json).json()

    def upload(self, path: str, filename: str, content: bytes, data: dict | None = None) -> Any:
        return self._request("POST", path, files={"archivo": (filename, content)}, data=data or {}).json()

    def download(self, path: str, **params) -> bytes:
        return self._request("GET", path, params={k: v for k, v in params.items() if v is not None}).content
