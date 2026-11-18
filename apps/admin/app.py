"""Ambiente 1 — Administrador / Investigador (diseño basado en ecnt-frontend).

Ejecutar:  streamlit run apps/admin/app.py --server.port 8501
Solo se comunica con la API REST (ecnt_client); no importa el núcleo de ML.
"""

import os

import streamlit as st
from vistas import analisis, datos, modelos, sistema

from ecnt_client import theme
from ecnt_client.ui import api, call, login_gate, logout

st.set_page_config(page_title="ECNT · Administrador", page_icon="🩺", layout="wide")

EPS_URL = os.environ.get("ECNT_EPS_APP_URL", "http://localhost:8502")
user = login_gate("Sistema de vigilancia y predicción de riesgo de enfermedades crónicas no transmisibles",
                  ("admin", "investigador"), env="admin", other_app=("Ir al portal EPS →", EPS_URL))
if user:
    theme.apply_theme("admin")
    sections = {
        "Menú principal": [
            st.Page(sistema.inicio, title="Dashboard", icon=":material/dashboard:", url_path="inicio", default=True),
            st.Page(datos.gestion, title="Datasets", icon=":material/database:", url_path="datasets"),
            st.Page(datos.carga_masiva, title="Carga masiva", icon=":material/upload_file:", url_path="carga"),
            st.Page(datos.formulario, title="Ingreso territorial", icon=":material/edit_note:", url_path="formulario"),
            st.Page(analisis.exploratorio, title="Análisis estadístico", icon=":material/bar_chart:", url_path="eda"),
            st.Page(analisis.limpieza, title="Limpieza de datos", icon=":material/cleaning_services:",
                    url_path="limpieza"),
            st.Page(analisis.variables, title="Selección de variables", icon=":material/checklist:",
                    url_path="variables"),
            st.Page(modelos.entrenamiento, title="Entrenamiento", icon=":material/psychology:",
                    url_path="entrenamiento"),
            st.Page(modelos.comparacion, title="Comparación", icon=":material/emoji_events:", url_path="comparacion"),
            st.Page(modelos.gestion, title="Gestión de modelos", icon=":material/verified:", url_path="modelos"),
            st.Page(modelos.datos_nuevos, title="Predicción", icon=":material/bolt:", url_path="prediccion"),
        ],
    }
    if user["rol"] == "admin":
        sections["Administración"] = [
            st.Page(sistema.reglas_alerta, title="Reglas de alerta", icon=":material/notifications_active:",
                    url_path="reglas"),
            st.Page(sistema.usuarios, title="Usuarios", icon=":material/group:", url_path="usuarios"),
            st.Page(sistema.auditoria, title="Auditoría", icon=":material/history:", url_path="auditoria"),
        ]
    st.session_state["_pages"] = {pg.url_path: pg for pages in sections.values() for pg in pages}
    page = st.navigation(sections, position="hidden")
    theme.sidebar("admin", sections, page, user, logout)
    abiertas = call(api().get, "/alerts", estado="nueva", quiet=True) or []
    theme.topbar("admin", user, page.title, notifications=len(abiertas))
    page.run()
