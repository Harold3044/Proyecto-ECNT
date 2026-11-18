"""Ambiente 1 — Administrador / Investigador.

Ejecutar:  streamlit run apps/admin/app.py --server.port 8501
Solo se comunica con la API REST (ecnt_client); no importa el núcleo de ML.
"""

import streamlit as st
from vistas import analisis, datos, modelos, sistema

from ecnt_client.ui import login_gate, sidebar_user

st.set_page_config(page_title="ECNT · Administrador", page_icon="🧪", layout="wide")

user = login_gate("Plataforma ECNT — Ambiente Administrador / Investigador", ("admin", "investigador"),
                  "Gestión de datos y desarrollo de modelos. Grupo 05 — Inteligencia Artificial.")
if user:
    sidebar_user(user)
    pages = {
        "General": [st.Page(sistema.inicio, title="Inicio", icon="🏠", url_path="inicio", default=True)],
        "Datos": [
            st.Page(datos.gestion, title="Gestión de datasets", icon="🗂️", url_path="datasets"),
            st.Page(datos.carga_masiva, title="Carga masiva", icon="⬆️", url_path="carga"),
            st.Page(datos.formulario, title="Ingreso territorial", icon="📝", url_path="formulario"),
        ],
        "Análisis": [
            st.Page(analisis.exploratorio, title="Estadística descriptiva", icon="📊", url_path="eda"),
            st.Page(analisis.limpieza, title="Limpieza y transformación", icon="🧹", url_path="limpieza"),
            st.Page(analisis.variables, title="Selección de variables", icon="🎯", url_path="variables"),
        ],
        "Modelos": [
            st.Page(modelos.entrenamiento, title="Partición y entrenamiento", icon="⚙️", url_path="entrenamiento"),
            st.Page(modelos.comparacion, title="Comparación de resultados", icon="📈", url_path="comparacion"),
            st.Page(modelos.gestion, title="Gestión de modelos", icon="🏷️", url_path="modelos"),
            st.Page(modelos.datos_nuevos, title="Pruebas con datos nuevos", icon="🧾", url_path="datos-nuevos"),
        ],
    }
    if user["rol"] == "admin":
        pages["Administración"] = [
            st.Page(sistema.reglas_alerta, title="Reglas de alerta", icon="🚨", url_path="reglas"),
            st.Page(sistema.usuarios, title="Usuarios", icon="👥", url_path="usuarios"),
            st.Page(sistema.auditoria, title="Auditoría", icon="📜", url_path="auditoria"),
        ]
    st.navigation(pages).run()
