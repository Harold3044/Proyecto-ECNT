"""Inicio (dashboard administrativo), reglas de alerta, usuarios y auditoría."""

from __future__ import annotations

import streamlit as st

from ecnt_client import theme
from ecnt_client.ui import api, call, df, fmt

TIPOS = {"percentil_prediccion": {"percentil": 80}, "exceso_observado": {}, "posible_subregistro": {},
         "umbral_absoluto": {"umbral": 250}}


def _link(url_path: str, label: str = "Abrir →") -> None:
    """Enlace a otra página del menú (las páginas las registra app.py en la sesión)."""
    pages = st.session_state.get("_pages", {})
    if url_path in pages:
        st.page_link(pages[url_path], label=label, icon=":material/arrow_outward:")


def inicio() -> None:
    theme.welcome("Panel de administración", "Bienvenido al sistema ECNT",
                  "Administra datasets, analiza información y gestiona los modelos de predicción del riesgo "
                  "territorial de enfermedades crónicas no transmisibles.")
    ds = call(api().get, "/datasets") or []
    models = call(api().get, "/models") or []
    exps = call(api().get, "/experiments") or []
    alerts = call(api().get, "/alerts") or []
    registros = sum(d["versiones"][-1]["filas"] for d in ds if d["versiones"])
    theme.stat_cards([
        ("database", "blue", "Datasets cargados", len(ds), f"{sum(len(d['versiones']) for d in ds)} versiones"),
        ("users", "green", "Registros territoriales", fmt(registros, 0), "Municipios-periodo (última versión)"),
        ("brain", "purple", "Modelos entrenados", len(models),
         f"{sum(m['estado'] in ('aprobado', 'publicado') for m in models)} aprobados o publicados"),
        ("trending", "orange", "Alertas abiertas", sum(a["estado"] not in ("cerrada", "descartada") for a in alerts),
         f"{len(exps)} experimentos realizados"),
    ])

    theme.section("Acciones rápidas", "Accede a las principales herramientas del sistema.")
    c = st.columns(3)
    for col, (ic, color, title, text, path) in zip(c, [
        ("upload", "blue", "Cargar datasets", "Importa archivos CSV o Excel para comenzar el análisis.", "carga"),
        ("chart", "green", "Análisis estadístico", "Explora variables y conoce las características de los datos.",
         "eda"),
        ("brain", "purple", "Entrenar modelos", "Configura y compara modelos de aprendizaje automático.",
         "entrenamiento"),
    ], strict=True):
        with col:
            theme.action_card(ic, color, title, text)
            _link(path)

    pub = next((m for m in models if m["estado"] == "publicado"), None)
    theme.section("Modelo publicado", "Modelo que hoy consulta el ambiente EPS.")
    if pub:
        mt = pub["metricas"]
        theme.stat_cards([
            ("trophy", "purple", "Modelo", pub["algoritmo"].replace("_", " ").title(), f"#{pub['id']} · publicado"),
            ("activity", "blue", "RMSE validación cruzada", fmt(mt["rmse_cv_media"], 2), "por 100.000 hab."),
            ("trending", "green", "R² en prueba", fmt(mt["r2_test"], 3), f"RMSE prueba {fmt(mt['rmse_test'], 2)}"),
            ("shield", "orange", "Intervalo de predicción", f"± {fmt(mt['semiancho_intervalo_90'], 1)}", "90 %"),
        ])
    else:
        theme.notice("<strong>No hay modelo publicado:</strong> la EPS no puede consultar resultados.", "warning",
                     "alert")

    theme.section("Actividad reciente", "Últimos movimientos realizados en la plataforma.")
    eventos = []
    for d in ds:
        for v in d["versiones"]:
            eventos.append((v["creado"], "database", "blue", f"Dataset «{d['nombre']}» v{v['numero']}",
                            v["descripcion"]))
    for e in exps:
        eventos.append((e["creado"], "brain", "purple", f"Experimento #{e['id']} · {e['algoritmo']}",
                        f"RMSE prueba {fmt(e['rmse_test'], 2)} · R² {fmt(e['r2_test'], 3)}"))
    eventos.sort(key=lambda x: x[0], reverse=True)
    if not eventos:
        theme.notice("No hay actividad reciente. Cuando cargues datasets o entrenes modelos, aparecerán aquí.",
                     "info", "file")
        _link("carga", "Cargar mi primer dataset →")
    else:
        rows = []
        for fecha, ic, color, title, text in eventos[:8]:
            bg, fg = theme.COLORS[color]
            rows.append([f'<span class="ecnt-ico" style="width:28px;height:28px;background:{bg};color:{fg}">'
                         f'{theme.icon(ic, 15)}</span>', f"<b>{theme.esc(title)}</b><br>"
                         f"<span class='ecnt-muted'>{theme.esc(text)}</span>", theme.esc(fecha[:16].replace('T', ' '))])
        theme.html_table(["", "Actividad", "Fecha"], rows)
    if any(d["es_sintetico"] for d in ds):
        theme.notice("Hay datasets <strong>SINTÉTICOS</strong> cargados: identifíquelos antes de usarlos en resultados.",
                     "warning", "alert")
    theme.notice("<strong>Importante:</strong> este sistema es una herramienta de apoyo para la vigilancia y la "
                 "predicción del riesgo territorial de enfermedades crónicas no transmisibles. No reemplaza el "
                 "diagnóstico ni la valoración de un profesional de salud.", "warning", "shield")


def reglas_alerta() -> None:
    theme.page_header("Reglas de alerta", "Criterios configurables y justificados para generar alertas poblacionales.")
    st.caption("Las alertas apoyan la planificación de acciones preventivas. No son diagnósticos médicos. "
               "Toda regla requiere una justificación metodológica.")
    rules = call(api().get, "/alert-rules") or []
    st.dataframe(df(rules), width="stretch", hide_index=True)
    t1, t2, t3 = st.tabs(["Editar regla", "Nueva regla", "Generar alertas"])
    with t1:
        if rules:
            r = next(x for x in rules if x["id"] == st.selectbox("Regla", [x["id"] for x in rules],
                                                                  format_func=lambda i: next(
                                                                      x["nombre"] for x in rules if x["id"] == i)))
            with st.form("edit_rule"):
                activa = st.checkbox("Activa", value=r["activa"])
                prioridad = st.selectbox("Prioridad", ["alta", "media", "baja"],
                                         index=["alta", "media", "baja"].index(r["prioridad"]))
                params = dict(r["parametros"])
                for k, v in params.items():
                    params[k] = st.number_input(k, value=float(v))
                just = st.text_area("Justificación", value=r["justificacion"])
                if st.form_submit_button("Guardar"):
                    if call(api().patch, f"/alert-rules/{r['id']}", {"activa": activa, "prioridad": prioridad,
                                                                     "parametros": params, "justificacion": just}):
                        st.success("Regla actualizada.")
    with t2:
        with st.form("new_rule"):
            nombre = st.text_input("Nombre")
            tipo = st.selectbox("Tipo", list(TIPOS))
            params = {k: st.number_input(k, value=float(v)) for k, v in TIPOS[tipo].items()}
            prioridad = st.selectbox("Prioridad ", ["alta", "media", "baja"])
            just = st.text_area("Justificación metodológica (mín. 20 caracteres)")
            if st.form_submit_button("Crear regla"):
                if call(api().post, "/alert-rules", {"nombre": nombre, "tipo": tipo, "parametros": params,
                                                     "prioridad": prioridad, "justificacion": just}):
                    st.success("Regla creada.")
    with t3:
        st.write("Evalúa las reglas activas sobre las predicciones del modelo publicado. No duplica alertas abiertas.")
        if st.button("Generar alertas ahora", type="primary"):
            r = call(api().post, "/alerts/generate")
            if r:
                st.success(f"Alertas nuevas: {r['creadas']} (reglas evaluadas: {r['reglas_evaluadas']}, "
                           f"territorios: {r['territorios']})")


def usuarios() -> None:
    theme.page_header("Usuarios", "Cuentas, roles y acceso a la plataforma.")
    users = call(api().get, "/users") or []
    st.dataframe(df(users), width="stretch", hide_index=True)
    with st.form("new_user"):
        st.subheader("Crear usuario")
        c1, c2 = st.columns(2)
        email = c1.text_input("Correo")
        nombre = c2.text_input("Nombre")
        rol = c1.selectbox("Rol", ["eps", "investigador", "admin"])
        pwd = c2.text_input("Contraseña (mín. 8 caracteres)", type="password")
        if st.form_submit_button("Crear"):
            if call(api().post, "/users", {"email": email, "nombre": nombre, "rol": rol, "password": pwd}):
                st.success("Usuario creado.")
    if users:
        st.subheader("Activar / desactivar")
        uid = st.selectbox("Usuario", [u["id"] for u in users],
                           format_func=lambda i: next(f"{u['email']} ({u['rol']})" for u in users if u["id"] == i))
        u = next(x for x in users if x["id"] == uid)
        if st.button("Desactivar" if u["activo"] else "Activar"):
            if call(api().patch, f"/users/{uid}", {"activo": not u["activo"]}):
                st.rerun()


def auditoria() -> None:
    theme.page_header("Registro de operaciones", "Auditoría de las acciones realizadas en la plataforma.")
    accion = st.text_input("Filtrar por acción (p. ej. publicar_modelo)")
    log = call(api().get, "/audit", limit=500, accion=accion or None) or []
    st.dataframe(df(log), width="stretch", hide_index=True)
