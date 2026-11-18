"""Inicio (dashboard administrativo), reglas de alerta, usuarios y auditoría."""

from __future__ import annotations

import streamlit as st

from ecnt_client.ui import api, call, df, fmt

TIPOS = {"percentil_prediccion": {"percentil": 80}, "exceso_observado": {}, "posible_subregistro": {},
         "umbral_absoluto": {"umbral": 250}}


def inicio() -> None:
    st.title("🏠 Panel del administrador")
    ds = call(api().get, "/datasets") or []
    models = call(api().get, "/models") or []
    exps = call(api().get, "/experiments") or []
    alerts = call(api().get, "/alerts") or []
    c = st.columns(5)
    c[0].metric("Datasets", len(ds))
    c[1].metric("Versiones de datos", sum(len(d["versiones"]) for d in ds))
    c[2].metric("Experimentos", len(exps))
    c[3].metric("Modelos aprobados/publicados", sum(m["estado"] in ("aprobado", "publicado") for m in models))
    c[4].metric("Alertas abiertas", sum(a["estado"] not in ("cerrada", "descartada") for a in alerts))
    pub = next((m for m in models if m["estado"] == "publicado"), None)
    st.subheader("Modelo publicado")
    if pub:
        mt = pub["metricas"]
        st.success(f"**#{pub['id']} · {pub['nombre']}** — objetivo `{pub['objetivo']}`")
        k = st.columns(4)
        k[0].metric("RMSE CV", fmt(mt["rmse_cv_media"], 2))
        k[1].metric("RMSE prueba", fmt(mt["rmse_test"], 2))
        k[2].metric("R² prueba", fmt(mt["r2_test"], 3))
        k[3].metric("Intervalo 90 %", f"± {fmt(mt['semiancho_intervalo_90'], 1)}")
    else:
        st.warning("No hay modelo publicado: la EPS no puede consultar resultados.")
    if any(d["es_sintetico"] for d in ds):
        st.warning("Hay datasets **SINTÉTICOS** cargados: identifíquelos antes de usarlos en resultados.")
    st.subheader("Flujo de trabajo")
    st.markdown("1. **Carga** de datos → 2. **Estadística descriptiva** y calidad → 3. **Limpieza** (nuevas "
                "versiones) → 4. **Selección de variables** → 5. **Partición y entrenamiento** → 6. **Comparación** "
                "→ 7. **Aprobación y publicación** → 8. Pruebas con **datos nuevos**.")


def reglas_alerta() -> None:
    st.title("🚨 Reglas de alerta")
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
    st.title("👥 Usuarios")
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
    st.title("📜 Registro de operaciones")
    accion = st.text_input("Filtrar por acción (p. ej. publicar_modelo)")
    log = call(api().get, "/audit", limit=500, accion=accion or None) or []
    st.dataframe(df(log), width="stretch", hide_index=True)
