"""Ambiente 2 — EPS / Usuario final (aplicación independiente).

Ejecutar:  streamlit run apps/eps/app.py --server.port 8502
Solo consume la API REST; no tiene acceso a los módulos de entrenamiento.
"""

import streamlit as st
import vistas_eps as v

from ecnt_client.ui import login_gate, sidebar_user

st.set_page_config(page_title="ECNT · EPS", page_icon="🩺", layout="wide")

user = login_gate("Plataforma ECNT — Consulta para EPS", ("eps", "admin"),
                  "Riesgo territorial de enfermedades crónicas no transmisibles asociado a determinantes sociales "
                  "en el Caribe colombiano.")
if user:
    sidebar_user(user)
    with st.sidebar:
        st.caption("Herramienta de apoyo a la planificación en salud pública. No realiza diagnósticos.")
    st.navigation({
        "Resultados": [
            st.Page(v.dashboard, title="Dashboard", icon="📊", url_path="dashboard", default=True),
            st.Page(v.consulta, title="Consulta territorial", icon="📍", url_path="consulta"),
            st.Page(v.analisis, title="Análisis poblacional", icon="⚖️", url_path="analisis"),
            st.Page(v.mapa, title="Mapa", icon="🗺️", url_path="mapa"),
        ],
        "Seguimiento": [
            st.Page(v.alertas, title="Alertas", icon="🚨", url_path="alertas"),
            st.Page(v.informes, title="Exportar informes", icon="📄", url_path="informes"),
        ],
    }).run()
