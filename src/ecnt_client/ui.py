"""Utilidades de interfaz Streamlit compartidas por las aplicaciones Admin y EPS."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pandas as pd
import plotly.io as pio
import streamlit as st

from ecnt_client import DEFAULT_URL, ApiClient, ApiError, theme

ESTADO_COLOR = {"nueva": "🔴", "en_revision": "🟠", "asignada": "🟡", "en_seguimiento": "🔵", "cerrada": "🟢",
                "descartada": "⚪"}
PRIORIDAD_COLOR = {"alta": "🔴", "media": "🟠", "baja": "🟢"}
NIVEL_COLOR = theme.RISK


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


def login_gate(app_name: str, allowed_roles: tuple[str, ...], subtitle: str = "", env: str = "admin",
               other_app: tuple[str, str] | None = None) -> dict | None:
    """Pantalla de inicio de sesión (diseño ecnt-frontend). Devuelve el usuario si hay sesión válida."""
    if "api" in st.session_state and "usuario" in st.session_state:
        return st.session_state["usuario"]
    theme.apply_theme(env)
    brand = "ECNT" if env == "admin" else "ECNT · EPS"
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid, st.container(key="login_card"):
        st.markdown(
            f'<div class="ecnt-login-head"><div class="logo">{theme.icon("activity", 30)}</div><h1>{brand}</h1>'
            f'<p class="subtitle">{theme.esc(subtitle or app_name)}</p>'
            f'<div class="welcome">{theme.icon("heart", 18)}<span>Bienvenido</span></div>'
            f'<p class="desc">Ingresa tus datos para acceder a la plataforma.</p></div>', unsafe_allow_html=True)
        with st.form("login", border=False):
            email = st.text_input("Correo electrónico", placeholder="usuario@ejemplo.com")
            pwd = st.text_input("Contraseña", type="password", placeholder="Ingresa tu contraseña")
            with st.expander("Configuración de conexión"):
                url = st.text_input("URL de la API", value=DEFAULT_URL)
            ok = st.form_submit_button("Iniciar sesión", type="primary", width="stretch")
        if other_app:
            st.link_button(other_app[0], other_app[1], width="stretch")
        st.markdown(f'<div class="ecnt-login-foot"><div class="security">{theme.icon("shield", 15)}'
                    f'<span>Acceso seguro a la plataforma</span></div>'
                    f'<footer>Proyecto académico ECNT · Grupo 05 © 2026</footer></div>', unsafe_allow_html=True)
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


def logout() -> None:
    for k in ("api", "usuario", "_terr_cache"):
        st.session_state.pop(k, None)
    st.rerun()


def variable_dictionary(rows: list[dict], key: str, title: str = "¿Qué significa cada variable?") -> None:
    """Diccionario de variables legible (nombre, unidad, explicación) dentro de un desplegable con buscador."""
    if not rows:
        return
    with st.expander(f"📖 {title}"):
        q = st.text_input("Buscar variable", key=f"dic_{key}", placeholder="p. ej. servicios, rural, tasa")
        d = pd.DataFrame(rows)
        if q:
            mask = d.apply(lambda r: q.lower() in " ".join(str(v).lower() for v in r.values), axis=1)
            d = d[mask]
        for grupo, g in d.groupby("grupo", sort=False):
            st.markdown(f"**{grupo}**")
            st.dataframe(g[["variable", "descripcion", "unidad", "explicacion"]].rename(columns={
                "descripcion": "nombre", "explicacion": "qué significa"}), width="stretch", hide_index=True,
                column_config={"qué significa": st.column_config.TextColumn(width="large")})


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
