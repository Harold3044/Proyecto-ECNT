"""Ambiente 2 — EPS / Usuario final (aplicación independiente, diseño basado en ecnt-frontend).

Ejecutar:  streamlit run apps/eps/app.py --server.port 8502
Solo consume la API REST; no tiene acceso a los módulos de entrenamiento.
"""

import os

import streamlit as st
import vistas_eps as v

from ecnt_client import theme
from ecnt_client.ui import api, call, login_gate, logout

st.set_page_config(page_title="ECNT · EPS", page_icon="🩺", layout="wide")

ADMIN_URL = os.environ.get("ECNT_ADMIN_APP_URL", "http://localhost:8501")
user = login_gate("Portal EPS · Riesgo territorial de enfermedades crónicas no transmisibles en el Caribe colombiano",
                  ("eps", "admin"), env="eps", other_app=("Ir al ambiente Administrador →", ADMIN_URL))
if user:
    theme.apply_theme("eps")
    sections = {
        "Menú": [
            st.Page(v.dashboard, title="Panel principal", icon=":material/dashboard:", url_path="dashboard",
                    default=True),
            st.Page(v.consulta, title="Territorios", icon=":material/location_on:", url_path="territorios"),
            st.Page(v.analisis, title="Análisis poblacional", icon=":material/compare_arrows:", url_path="analisis"),
            st.Page(v.mapa, title="Mapa", icon=":material/map:", url_path="mapa"),
            st.Page(v.alertas, title="Alertas", icon=":material/warning:", url_path="alertas"),
            st.Page(v.informes, title="Informes", icon=":material/download:", url_path="informes"),
            st.Page(v.diccionario, title="Diccionario de variables", icon=":material/menu_book:",
                    url_path="diccionario"),
        ],
    }
    st.session_state["_pages"] = {pg.url_path: pg for pages in sections.values() for pg in pages}
    page = st.navigation(sections, position="hidden")
    theme.sidebar("eps", sections, page, user, logout)
    abiertas = call(api().get, "/alerts", estado="nueva", quiet=True) or []
    theme.topbar("eps", user, page.title, notifications=len(abiertas))
    page.run()
