"""Utilidades de interfaz Streamlit compartidas por las aplicaciones Admin y EPS."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pandas as pd
import plotly.io as pio
import streamlit as st

from ecnt_client import DEFAULT_URL, ApiClient, ApiError

ESTADO_COLOR = {"nueva": "🔴", "en_revision": "🟠", "asignada": "🟡", "en_seguimiento": "🔵", "cerrada": "🟢",
                "descartada": "⚪"}
PRIORIDAD_COLOR = {"alta": "🔴", "media": "🟠", "baja": "🟢"}
NIVEL_COLOR = {"muy bajo": "#1a9850", "bajo": "#91cf60", "medio": "#fee08b", "alto": "#fc8d59", "muy alto": "#d73027"}


def api() -> ApiClient:
    return st.session_state["api"]


def call(fn: Callable, *args, quiet: bool = False, **kwargs) -> Any:
    """Ejecuta una llamada a la API y muestra el error de forma comprensible."""
    try:
        return fn(*args, **kwargs)
    except ApiError as e:
        if not quiet:
            st.error(f"**Error {e.status}:** {e.message}")
            if e.validacion:
                validation_report(e.validacion)
        if e.status == 401:
            st.session_state.pop("api", None)
            st.session_state.pop("usuario", None)
        return None


def login_gate(app_name: str, allowed_roles: tuple[str, ...], subtitle: str = "") -> dict | None:
    """Muestra el formulario de inicio de sesión si no hay sesión válida. Devuelve el usuario."""
    if "api" in st.session_state and "usuario" in st.session_state:
        return st.session_state["usuario"]
    st.title(app_name)
    if subtitle:
        st.caption(subtitle)
    with st.form("login"):
        email = st.text_input("Correo electrónico")
        pwd = st.text_input("Contraseña", type="password")
        url = st.text_input("URL de la API", value=DEFAULT_URL)
        ok = st.form_submit_button("Ingresar", type="primary")
    if ok:
        client = ApiClient(url)
        data = call(client.login, email, pwd)
        if data:
            if data["usuario"]["rol"] not in allowed_roles:
                st.error(f"Su rol ('{data['usuario']['rol']}') no tiene acceso a esta aplicación.")
                return None
            st.session_state["api"] = client
            st.session_state["usuario"] = data["usuario"]
            st.rerun()
    return None


def sidebar_user(user: dict) -> None:
    with st.sidebar:
        st.markdown(f"**{user['nombre']}**  \n`{user['email']}` · rol **{user['rol']}**")
        if st.button("Cerrar sesión", width="stretch"):
            for k in ("api", "usuario"):
                st.session_state.pop(k, None)
            st.rerun()


def plot(fig_json: dict | None, key: str | None = None) -> None:
    if fig_json:
        st.plotly_chart(pio.from_json(json.dumps(fig_json)), width="stretch", key=key)


def df(rows: list[dict] | None) -> pd.DataFrame:
    return pd.DataFrame(rows or [])


def validation_report(rep: dict) -> None:
    issues = pd.DataFrame(rep.get("issues", []))
    if issues.empty:
        st.success("Sin observaciones de validación.")
        return
    errors = issues[issues.level == "error"]
    warns = issues[issues.level == "warning"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Errores (bloquean)", len(errors))
    c2.metric("Advertencias", len(warns))
    c3.metric("Informativas", int((issues.level == "info").sum()))
    cols = [c for c in ("level", "code", "column", "count", "message") if c in issues]
    st.dataframe(issues[cols].rename(columns={"level": "nivel", "code": "código", "column": "columna",
                                              "count": "conteo", "message": "mensaje"}),
                 width="stretch", hide_index=True)


def fmt(x, nd: int = 1) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    return f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")
