"""Módulos 2, 3 y 4: análisis exploratorio, limpieza/transformación y selección de variables."""

from __future__ import annotations

import streamlit as st

from ecnt_client import theme
from ecnt_client.ui import api, call, df, plot, validation_report, variable_dictionary
from vistas.comun import describe, version_selector

TARGET = "tasa_mort_ecnt_std"


def exploratorio() -> None:
    theme.page_header("Análisis exploratorio y estadística descriptiva", "Estadísticas descriptivas, calidad de datos, distribuciones, frecuencias y correlaciones.")
    v = version_selector("eda")
    if not v:
        return
    e = call(api().get, f"/datasets/versions/{v['id']}/eda")
    if not e:
        return
    q = e["calidad"]
    c = st.columns(6)
    c[0].metric("Registros", q["filas"])
    c[1].metric("Variables", q["columnas"])
    c[2].metric("Celdas nulas", f"{q['celdas_nulas']} ({q['pct_celdas_nulas']} %)")
    c[3].metric("Filas duplicadas", q["filas_duplicadas"])
    c[4].metric("Llaves duplicadas", q["llaves_duplicadas"] if q["llaves_duplicadas"] is not None else "—")
    c[5].metric("Válido", "Sí" if q["es_valido"] else "No")

    t1, t2, t3, t4, t5 = st.tabs(["Descriptivas", "Calidad de datos", "Distribuciones", "Frecuencias",
                                  "Correlaciones"])
    with t1:
        st.caption("Media, mediana, moda, desviación estándar, mínimos, máximos, cuartiles, asimetría, curtosis "
                   "y atípicos según el criterio IQR (1,5 × rango intercuartílico).")
        names = {d["variable"]: d["descripcion"] + (f" ({d['unidad']})" if d["unidad"] else "")
                 for d in e.get("diccionario", [])}
        desc = df(e["descriptivas"])
        if not desc.empty:
            desc.insert(1, "nombre", desc["variable"].map(names))
        st.dataframe(desc.round(3), width="stretch", hide_index=True)
        variable_dictionary(e.get("diccionario"), f"eda_{v['id']}")
    with t2:
        st.caption("Valores nulos, duplicados, inconsistencias, rangos, tipos incorrectos e información insuficiente.")
        validation_report(e["validacion"])
        plot(call(api().get, f"/datasets/versions/{v['id']}/eda/plot", kind="missing", quiet=True), "miss")
    with t3:
        num = e["numericas"]
        if not num:
            st.info("No hay variables numéricas.")
        else:
            c1, c2 = st.columns(2)
            col = c1.selectbox("Variable", num, index=num.index(TARGET) if TARGET in num else 0)
            grp = c2.selectbox("Agrupar por (diagrama de caja)", ["(ninguno)", *e["categoricas"]])
            plot(call(api().get, f"/datasets/versions/{v['id']}/eda/plot", kind="histogram", column=col), "hist")
            if grp != "(ninguno)":
                plot(call(api().get, f"/datasets/versions/{v['id']}/eda/plot", kind="box", column=col, group=grp),
                     "box")
            if TARGET in num and col != TARGET:
                plot(call(api().get, f"/datasets/versions/{v['id']}/eda/plot", kind="scatter", column=col,
                          target=TARGET, group=grp if grp != "(ninguno)" else None), "scatter")
    with t4:
        cats = e["categoricas"]
        if cats:
            col = st.selectbox("Variable categórica", cats)
            fr = call(api().get, f"/datasets/versions/{v['id']}/eda/frequencies", column=col)
            if fr:
                plot(fr["grafico"], "freq")
                st.dataframe(df(fr["tabla"]), width="stretch", hide_index=True)
        else:
            st.info("No hay variables categóricas con pocos niveles.")
    with t5:
        m = st.radio("Método", ["spearman", "pearson", "kendall"], horizontal=True)
        cr = call(api().get, f"/datasets/versions/{v['id']}/eda/correlation", method=m,
                  target=TARGET if TARGET in e["numericas"] else None)
        if cr:
            plot(cr["grafico"], "corr")
            if "con_objetivo" in cr:
                st.markdown(f"**Correlación con la variable objetivo** (`{TARGET}`)")
                st.dataframe(df(cr["con_objetivo"]).round(3), width="stretch", hide_index=True)


def _step_form(op: str, columns: list[str]) -> dict | None:
    """Formulario de parámetros según la operación de limpieza elegida."""
    p: dict = {"op": op}
    if op in ("drop_columns", "cast_numeric", "impute", "clip_outliers_iqr", "log1p", "one_hot", "standardize",
              "drop_missing"):
        p["columns"] = st.multiselect("Columnas", columns)
        if not p["columns"] and op != "drop_missing":
            return None
    if op == "drop_duplicates":
        sub = st.multiselect("Llave (vacío = fila completa)", columns)
        if sub:
            p["subset"] = sub
    if op == "impute":
        p["strategy"] = st.selectbox("Estrategia", ["median", "mean", "mode", "constant"])
        if p["strategy"] == "constant":
            p["value"] = st.number_input("Valor", value=0.0)
    if op == "clip_outliers_iqr":
        p["k"] = st.number_input("k (IQR)", value=1.5, min_value=0.5, max_value=5.0)
    if op == "cast_numeric":
        p["decimal"] = st.selectbox("Separador decimal", [".", ","])
    if op in ("clip_range", "set_null_out_of_range"):
        p["column"] = st.selectbox("Columna", columns)
        c1, c2 = st.columns(2)
        p["min"] = c1.number_input("Mínimo", value=None)
        p["max"] = c2.number_input("Máximo", value=None)
    if op == "filter_rows":
        p["column"] = st.selectbox("Columna", columns)
        p["operator"] = st.selectbox("Operador", ["==", "!=", ">", ">=", "<", "<=", "notnull"])
        raw = st.text_input("Valor")
        try:
            p["value"] = float(raw)
        except ValueError:
            p["value"] = raw
    if op == "one_hot":
        p["drop_first"] = st.checkbox("Eliminar primera categoría")
    return p


def limpieza() -> None:
    theme.page_header("Limpieza y transformación", "Tratamiento de faltantes, duplicados, formatos, atípicos y codificación con versionado.")
    st.caption("Cada aplicación crea una **nueva versión**; el dataset original se conserva. Para modelar, la "
               "imputación, el escalado y la codificación se ajustan automáticamente dentro del pipeline con datos "
               "de entrenamiento, por lo que aquí son opcionales.")
    v = version_selector("clean")
    if not v:
        return
    rows = call(api().get, f"/datasets/versions/{v['id']}/rows", limit=1)
    ops = call(api().get, "/catalog/cleaning-operations") or []
    if not rows:
        return
    columns = rows["columnas"]
    key = f"steps_{v['id']}"
    st.session_state.setdefault(key, [])
    labels = {o["op"]: f"{o['op']} — {o['descripcion']}" for o in ops}
    op = st.selectbox("Operación", list(labels), format_func=lambda o: labels[o])
    if next(o for o in ops if o["op"] == op)["usa_estadisticos_globales"]:
        st.warning("Esta operación usa estadísticos de todo el dataset. Úsela con fines exploratorios o de "
                   "corrección de datos; el modelado aplica sus propias transformaciones sin fuga de información.")
    params = _step_form(op, columns)
    if st.button("➕ Agregar paso", disabled=params is None):
        st.session_state[key].append(params)
    steps = st.session_state[key]
    if steps:
        st.markdown("**Pasos a aplicar**")
        st.json(steps)
        prev = call(api().post, f"/datasets/versions/{v['id']}/clean/preview", {"pasos": steps})
        confirm_needed = False
        if prev:
            theme.section("Vista previa del resultado", "Simulación: todavía no se ha creado ninguna versión.")
            k = st.columns(3)
            k[0].metric("Filas", f"{prev['filas_antes']} → {prev['filas_despues']}")
            k[1].metric("Columnas", f"{prev['columnas_antes']} → {prev['columnas_despues']}")
            k[2].metric("Filas eliminadas", f"{100 * prev['pct_filas_eliminadas']:.1f} %")
            for w in prev["advertencias"]:
                theme.notice(f"<strong>Atención:</strong> {theme.esc(w)}", "danger", "alert")
                confirm_needed = True
            with st.expander("Primeras filas del resultado"):
                st.dataframe(df(prev["vista_previa"]), width="stretch", hide_index=True)
        ok_confirm = (not confirm_needed) or st.checkbox("Entiendo el impacto y quiero crear la versión de todos modos")
        desc = st.text_input("Descripción de la versión", placeholder="p. ej. Eliminación de duplicados por llave")
        c1, c2 = st.columns(2)
        if c1.button("Aplicar y crear versión", type="primary", disabled=not prev or not ok_confirm):
            r = call(api().post, f"/datasets/versions/{v['id']}/clean", {"pasos": steps, "descripcion": desc})
            if r:
                st.session_state[key] = []
                st.success(f"Versión v{r['numero']} creada: {r['filas']} filas × {r['columnas']} columnas.")
                for s in r["operaciones"]:
                    st.write(f"• Paso {s['paso']} `{s['op']}`: {s['filas_antes']}→{s['filas_despues']} filas, "
                             f"{s['columnas_antes']}→{s['columnas_despues']} columnas · {s['detalle']}")
        if c2.button("Vaciar pasos"):
            st.session_state[key] = []
            st.rerun()


def variables() -> None:
    theme.page_header("Selección de variables", "Ranking de relevancia, multicolinealidad y regresión múltiple calculados solo con entrenamiento.")
    st.caption("El ranking, el VIF y la regresión OLS se calculan **solo con la partición de entrenamiento**, "
               "para evitar fuga de información hacia el conjunto de prueba.")
    v = version_selector("feat")
    if not v:
        return
    c1, c2, c3 = st.columns(3)
    target = c1.text_input("Variable objetivo", value=TARGET)
    ratio = c2.selectbox("Partición", ["70/30", "75/25", "80/20", "90/10"], index=2)
    seed = c3.number_input("Semilla", value=42, step=1)
    if not st.button("Calcular relevancia", type="primary"):
        return
    with st.spinner("Calculando…"):
        r = call(api().post, f"/datasets/versions/{v['id']}/features",
                 {"objetivo": target, "proporcion": ratio, "semilla": int(seed)})
    if not r:
        return
    st.caption(f"Entrenamiento: {r['n_entrenamiento']} territorios · Prueba excluida: {r['n_prueba_excluida']}")
    t1, t2, t3, t4 = st.tabs(["Ranking", "Multicolinealidad (VIF)", "Regresión múltiple (OLS)", "Correlación"])
    with t1:
        st.markdown("Criterios: |Spearman|, estadístico F, información mutua e importancia de Random Forest. "
                    "`rank_promedio` = 1 es la variable más relevante.")
        plot(r["grafico_ranking"], "rank")
        rk = df(r["ranking"])
        rk.insert(1, "nombre", rk["variable"].map(lambda c: describe(c)))
        st.dataframe(rk, width="stretch", hide_index=True)
    with t2:
        st.markdown("VIF > 10 indica colinealidad alta: conviene no usar juntas esas variables en la regresión lineal.")
        st.dataframe(df(r["vif"]), width="stretch", hide_index=True)
    with t3:
        s = r["ols_resumen"]
        c = st.columns(3)
        c[0].metric("R²", f"{s['r2']:.3f}")
        c[1].metric("R² ajustado", f"{s['r2_ajustado']:.3f}")
        c[2].metric("p‑valor F", f"{s['f_pvalor']:.2e}")
        st.caption("Coeficientes estandarizados: asociaciones, no efectos causales.")
        st.dataframe(df(r["ols"]), width="stretch", hide_index=True)
    with t4:
        plot(r["grafico_correlacion"], "corrtrain")
