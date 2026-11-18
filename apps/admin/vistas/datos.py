"""Módulo 1: gestión y carga de datos (historial, carga masiva, ingreso territorial por formulario)."""

from __future__ import annotations

import streamlit as st

from ecnt_client import theme
from ecnt_client.ui import api, call, df, validation_report
from vistas.comun import datasets, version_selector

ROLES_DS = {"(ninguno)": None, "modelado": "modelado", "panel histórico": "panel", "validación externa": "externo"}


def gestion() -> None:
    theme.page_header("Gestión de datasets", "Historial de archivos cargados, versiones, linaje de transformaciones y diccionario de variables.")
    st.caption("Historial de archivos cargados, versiones, linaje de transformaciones y origen de los datos.")
    ds = datasets()
    if not ds:
        st.info("No hay datasets.")
        return
    table = df([{"id": d["id"], "nombre": d["nombre"], "origen": d["origen"], "rol": d["rol"], "fuente": d["fuente"],
                 "sintético": d["es_sintetico"], "versiones": len(d["versiones"]),
                 "última": f"v{d['versiones'][-1]['numero']} ({d['versiones'][-1]['filas']} filas)",
                 "creado": d["creado"][:16]} for d in ds])
    st.dataframe(table, width="stretch", hide_index=True)

    st.subheader("Detalle de una versión")
    v = version_selector("gestion")
    if not v:
        return
    full = call(api().get, f"/datasets/versions/{v['id']}")
    if not full:
        return
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros", full["filas"])
    c2.metric("Variables", full["columnas"])
    c3.metric("Versión", f"v{full['numero']}")
    c4.metric("Versión padre", full["padre_id"] or "— (original)")
    st.caption(f"Huella SHA‑256: `{full['sha256']}` · Fuente: {v['dataset']['fuente'] or '—'}")
    t1, t2, t3, t4 = st.tabs(["Datos", "Linaje", "Validación", "Diccionario de variables"])
    with t1:
        rows = call(api().get, f"/datasets/versions/{v['id']}/rows", limit=200)
        if rows:
            st.caption(f"Mostrando {len(rows['filas'])} de {rows['total']} registros")
            st.dataframe(df(rows["filas"]), width="stretch", hide_index=True)
        if st.button("Preparar descarga CSV"):
            content = call(api().download, f"/datasets/versions/{v['id']}/download")
            if content:
                st.download_button("Descargar", content, f"dataset_{v['dataset']['id']}_v{full['numero']}.csv",
                                   "text/csv")
    with t2:
        for op in full["operaciones"]:
            with st.expander(f"Paso {op.get('paso', '')} · {op.get('op')}"):
                st.json(op)
    with t3:
        validation_report(full["validacion"])
    with t4:
        e = call(api().get, f"/datasets/versions/{v['id']}/eda", quiet=True)
        if e:
            st.caption("Qué significa cada columna de esta versión del dataset (fuente: diccionario del proyecto).")
            d = df(e["diccionario"])
            st.dataframe(d[["variable", "descripcion", "unidad", "grupo", "explicacion", "fuente"]].rename(columns={
                "descripcion": "nombre", "explicacion": "qué significa"}), width="stretch", hide_index=True,
                column_config={"qué significa": st.column_config.TextColumn(width="large")})


def carga_masiva() -> None:
    theme.page_header("Carga masiva de datos", "Importa archivos CSV o Excel; se validan antes de guardarse y el original se conserva.")
    st.caption("Archivos CSV (separador y codificación automáticos) o Excel. El archivo original se conserva "
               "sin cambios y se valida antes de guardarse.")
    f = st.file_uploader("Archivo", type=["csv", "xlsx", "xls"])
    if not f:
        return
    content = f.getvalue()
    pre = call(api().upload, "/datasets/validate", f.name, content)
    if not pre:
        return
    st.subheader("Vista previa e identificación de columnas")
    st.dataframe(df(pre["vista_previa"]), width="stretch", hide_index=True)
    cols = df(pre["validacion"]["columns"])
    if not cols.empty:
        st.dataframe(cols.rename(columns={"name": "columna", "dtype": "tipo", "kind": "clase",
                                          "catalogada": "en diccionario", "nulos": "nulos", "unicos": "únicos"}),
                     width="stretch", hide_index=True)
    st.subheader("Validación")
    validation_report(pre["validacion"])
    if not pre["validacion"]["is_valid"]:
        st.error("El archivo tiene errores bloqueantes y no puede cargarse. Corrija la fuente y vuelva a intentar.")
        return
    with st.form("carga"):
        nombre = st.text_input("Nombre del dataset", value=f.name.rsplit(".", 1)[0])
        fuente = st.text_input("Origen / fuente de los datos", placeholder="p. ej. DANE — NBI CNPV 2018")
        desc = st.text_area("Descripción")
        rol = st.selectbox("Uso del dataset", list(ROLES_DS))
        sint = st.checkbox("Los datos son SINTÉTICOS (no reales)")
        if st.form_submit_button("Cargar dataset", type="primary"):
            r = call(api().upload, "/datasets/upload", f.name, content,
                     {"nombre": nombre, "fuente": fuente, "descripcion": desc, "rol": ROLES_DS[rol] or "",
                      "es_sintetico": str(sint).lower()})
            if r:
                st.success(f"Dataset #{r['dataset']['id']} cargado: {r['version']['filas']} registros, "
                           f"{r['version']['columnas']} variables (versión original v1).")


def formulario() -> None:
    theme.page_header("Ingreso territorial por formulario", "Registra una observación territorial (municipio y periodo) campo por campo.")
    st.info("Cada registro es una **observación territorial** (municipio y periodo), no una persona.")
    cat = call(api().get, "/catalog/variables")
    if not cat:
        return
    variables = [v for v in cat["variables"] if v["kind"] in ("numeric", "target")]
    modo = st.radio("Destino", ["Agregar a un dataset existente (nueva versión)", "Crear un dataset nuevo"],
                    horizontal=True)
    target_version = None
    if modo.startswith("Agregar"):
        target_version = version_selector("form")
        if not target_version:
            return
    with st.form("registro", clear_on_submit=False):
        c1, c2, c3, c4 = st.columns(4)
        rec = {
            "divipola": c1.text_input("Código DIVIPOLA (5 dígitos)*", max_chars=5),
            "municipio": c2.text_input("Municipio*"),
            "departamento": c3.text_input("Departamento"),
            "periodo": c4.text_input("Periodo", value="2018-2019"),
        }
        st.markdown("**Determinantes sociales y demográficos** (deje vacío si no hay dato)")
        grid = st.columns(3)
        for i, v in enumerate(variables):
            label = f"{v['name']} ({v['unit']})" if v["unit"] else v["name"]
            lo = None if v["min"] is None else float(v["min"])
            hi = None if v["max"] is None else float(v["max"])
            val = grid[i % 3].number_input(label, value=None, min_value=lo, max_value=hi, help=v["explicacion"] or v["description"],
                                           key=f"f_{v['name']}", format="%.4f")
            if val is not None:
                rec[v["name"]] = val
        nombre = ""
        if not target_version:
            nombre = st.text_input("Nombre del nuevo dataset*")
        sint = st.checkbox("Registro SINTÉTICO (de prueba)")
        enviar = st.form_submit_button("Guardar registro", type="primary")
    if enviar:
        if not rec["divipola"] or not rec["municipio"]:
            st.error("DIVIPOLA y municipio son obligatorios.")
            return
        if sint:
            rec["es_sintetico"] = True
        if target_version:
            r = call(api().post, f"/datasets/versions/{target_version['id']}/records", {"registros": [rec]})
            if r:
                st.success(f"Registro agregado. Nueva versión v{r['numero']} con {r['filas']} registros.")
        else:
            if not nombre:
                st.error("Indique el nombre del dataset.")
                return
            r = call(api().post, "/datasets/form", {"nombre": nombre, "registros": [rec], "es_sintetico": sint,
                                                     "fuente": "Formulario de ingreso territorial"})
            if r:
                st.success(f"Dataset #{r['dataset']['id']} creado (v1).")
