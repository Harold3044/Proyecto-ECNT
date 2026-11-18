"""Módulos 5–9: partición, entrenamiento, comparación, gestión de modelos y pruebas con datos nuevos."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ecnt_client import theme
from ecnt_client.ui import api, call, df, fmt, plot
from vistas.comun import datasets, describe, numeric_columns, version_selector

TARGET = "tasa_mort_ecnt_std"
NON_PRED = {"divipola", "cod_depto", "def_ecnt_2018_2019", "personas_anio_2018_2019", "anios_con_registro", TARGET}
ESTADO_ICON = {"evaluado": "🔵", "aprobado": "🟡", "publicado": "🟢", "retirado": "⚪"}


def _hyperparams(algo: dict) -> dict:
    out = {}
    for name, p in algo["hiperparametros"].items():
        key = f"hp_{algo['key']}_{name}"
        if p["type"] == "int":
            out[name] = st.number_input(f"{name}", int(p["min"]), int(p["max"]), int(p["default"]), help=p["help"],
                                        key=key)
        elif p["type"] == "float":
            out[name] = st.number_input(f"{name}", float(p["min"]), float(p["max"]), float(p["default"]),
                                        help=p["help"], key=key, format="%.4f")
        else:
            out[name] = st.selectbox(name, p["choices"], index=list(p["choices"]).index(p["default"]), key=key)
    return out


def _show_comparison(res: dict) -> None:
    st.subheader("Resultados")
    t = df(res["tabla"])
    cols = ["algoritmo", "nombre", "rmse_cv_media", "rmse_cv_de", "mae_cv_media", "r2_cv_media", "rmse_test",
            "mae_test", "r2_test", "rmse_entrenamiento", "version_modelo_id"]
    st.dataframe(t[[c for c in cols if c in t]].round(3), width="stretch", hide_index=True)
    sel = res.get("seleccion") or {}
    if sel.get("elegido"):
        st.success(f"**Modelo recomendado: {sel['elegido']}** — {sel['razon']}")
    else:
        st.error(sel.get("razon", "Sin selección"))
    c1, c2 = st.columns(2)
    with c1:
        plot(res.get("grafico_rmse"), "cmp_rmse")
    with c2:
        plot(res.get("grafico_r2"), "cmp_r2")
    st.caption("Criterio: superar la línea base y elegir el modelo más simple dentro de 1 error estándar del menor "
               "RMSE de validación cruzada. El conjunto de prueba no interviene en la selección.")


def entrenamiento() -> None:
    theme.page_header("Partición y entrenamiento", "Configura la partición, las variables, los modelos y sus hiperparámetros.")
    v = version_selector("train")
    if not v:
        return
    cat = call(api().get, "/catalog/algorithms") or []
    cols = [c for c in numeric_columns(v["id"]) if c not in NON_PRED]

    st.subheader("1. Partición de los datos")
    c1, c2, c3, c4 = st.columns(4)
    ratio = c1.selectbox("Entrenamiento / prueba", ["70/30", "75/25", "80/20", "90/10"], index=2)
    seed = c2.number_input("Semilla aleatoria", value=42, step=1)
    strategy = c3.selectbox("Estrategia", ["aleatoria", "geografica", "agrupada"],
                            help="aleatoria: por territorio (estratificada por el objetivo); geográfica: "
                                 "departamentos completos en prueba; agrupada: grupos completos (paneles)")
    group_col = c4.text_input("Columna de grupo", value="cod_depto" if strategy == "geografica" else "",
                              disabled=strategy == "aleatoria")
    test_groups = None
    if strategy == "geografica":
        g = st.text_input("Departamentos de prueba (códigos separados por coma; vacío = al azar)", value="")
        test_groups = [x.strip() for x in g.split(",") if x.strip()] or None
    c1, c2 = st.columns(2)
    cv_splits = c1.slider("Pliegues de validación cruzada", 3, 10, 5)
    cv_repeats = c2.slider("Repeticiones de la validación cruzada", 1, 5, 3)

    st.subheader("2. Variables")
    target = st.text_input("Variable objetivo", value=TARGET)
    feats = st.multiselect("Variables predictoras", [c for c in cols if c != target], format_func=describe,
                           default=[c for c in cols if c != target])
    c1, c2 = st.columns(2)
    sel = c1.selectbox("Selección automática (dentro de entrenamiento)", ["none", "ranking_top_k", "kbest"],
                       format_func={"none": "Ninguna", "ranking_top_k": "Top k del ranking combinado",
                                    "kbest": "SelectKBest dentro del pipeline (F de regresión)"}.get)
    k = c2.number_input("k", 1, max(1, len(feats)), min(8, max(1, len(feats))), disabled=sel == "none")

    st.subheader("3. Modelos e hiperparámetros")
    names = {a["key"]: a["nombre"] for a in cat}
    algos = st.multiselect("Algoritmos a entrenar", list(names), format_func=names.get,
                           default=["baseline", "linear", "ridge", "random_forest", "gradient_boosting"])
    tune = st.checkbox("Ajustar hiperparámetros automáticamente (búsqueda en rejilla con CV en entrenamiento)",
                       value=False)
    params: dict[str, dict] = {}
    if not tune:
        for a in cat:
            if a["key"] in algos and a["hiperparametros"]:
                with st.expander(f"Hiperparámetros · {a['nombre']}"):
                    params[a["key"]] = _hyperparams(a)
    if not feats or len(algos) < 1:
        st.warning("Seleccione variables y al menos un algoritmo.")
        return
    base = {"target": target, "features": feats, "ratio": ratio, "seed": int(seed), "split_strategy": strategy,
            "group_col": group_col or None, "test_groups": test_groups, "cv_splits": cv_splits,
            "cv_repeats": cv_repeats, "selection": sel, "select_k": int(k) if sel != "none" else None, "tune": tune}
    if st.button("🚀 Entrenar", type="primary"):
        with st.spinner("Entrenando y validando… (puede tardar hasta 1–2 minutos)"):
            if len(algos) == 1:
                r = call(api().post, "/experiments", {"dataset_version_id": v["id"],
                                                      "config": {**base, "algorithm": algos[0],
                                                                 "params": params.get(algos[0], {})}})
                if r:
                    st.success(f"Experimento #{r['experimento']['id']} guardado; versión de modelo "
                               f"#{r['version_modelo']['id']} en estado 'evaluado'.")
                    st.session_state["ultimo_experimento"] = r["experimento"]["id"]
            else:
                # Misma partición, variables y semilla para todos; hiperparámetros propios de cada algoritmo
                r = call(api().post, "/experiments/compare", {"dataset_version_id": v["id"], "config": base,
                                                              "algoritmos": algos, "parametros": params})
                if r:
                    st.session_state["ultima_comparacion"] = r
                    _show_comparison(r)


def _experiment_detail(exp_id: int) -> None:
    e = call(api().get, f"/experiments/{exp_id}")
    if not e:
        return
    s = e["resumen"]
    c = st.columns(5)
    c[0].metric("RMSE CV", f"{fmt(s['rmse_cv_media'], 2)} ± {fmt(s['rmse_cv_de'], 2)}")
    c[1].metric("RMSE prueba", fmt(s["rmse_test"], 2))
    c[2].metric("MAE prueba", fmt(s["mae_test"], 2))
    c[3].metric("R² prueba", fmt(s["r2_test"], 3))
    c[4].metric("Intervalo 90 %", f"± {fmt(s['semiancho_intervalo_90'], 1)}")
    ci = s["ic95_test"]
    st.caption(f"IC 95 % bootstrap (prueba): RMSE [{fmt(ci['rmse'][0], 1)}; {fmt(ci['rmse'][1], 1)}], R² "
               f"[{fmt(ci['r2'][0], 2)}; {fmt(ci['r2'][1], 2)}] · n entrenamiento {s['n_entrenamiento']}, prueba "
               f"{s['n_prueba']} · partición {s['particion']['strategy']} {s['particion']['test_size']:.0%} · semilla "
               f"{s['particion']['seed']} · cobertura del intervalo en prueba "
               f"{fmt(100 * s['cobertura_intervalo_90_test'], 0)} %")
    p = call(api().get, f"/experiments/{exp_id}/plots") or {}
    c1, c2 = st.columns(2)
    with c1:
        plot(p.get("real_vs_predicho"), f"rv{exp_id}")
        plot(p.get("histograma_residuos"), f"rh{exp_id}")
    with c2:
        plot(p.get("residuos"), f"rr{exp_id}")
        plot(p.get("importancia"), f"ri{exp_id}")
    t1, t2, t3, t4 = st.tabs(["Desempeño por departamento", "Interpretación del modelo", "Predicciones de prueba",
                              "Configuración"])
    with t1:
        st.dataframe(df(s.get("metricas_por_grupo")), width="stretch", hide_index=True)
        st.caption("Grupos con menos de 3 territorios en prueba no tienen métricas.")
    with t2:
        st.dataframe(df(s.get("interpretacion_modelo")), width="stretch", hide_index=True)
    with t3:
        st.dataframe(df(s.get("predicciones_prueba")).round(2), width="stretch", hide_index=True)
    with t4:
        st.json({"parametros": s["parametros"], "variables": s["variables"], "ajuste": s.get("ajuste_hiperparametros"),
                 "entorno": s["entorno"], "huella_datos": s["huella_datos"]})


def comparacion() -> None:
    theme.page_header("Comparación y evaluación de modelos", "MAE, RMSE y R², gráficos comparativos, real vs. predicho y análisis de residuos.")
    exps = call(api().get, "/experiments") or []
    if not exps:
        st.info("Aún no hay experimentos.")
        return
    t = df(exps)
    groups = [g for g in t["grupo_comparacion"].dropna().unique()]
    tab1, tab2 = st.tabs(["Comparaciones", "Detalle de un experimento"])
    with tab1:
        if groups:
            g = st.selectbox("Grupo de comparación", groups,
                             format_func=lambda x: f"{x} · {len(t[t.grupo_comparacion == x])} modelos · "
                                                   f"{t[t.grupo_comparacion == x].creado.min()[:16]}")
            r = call(api().get, f"/experiments/groups/{g}")
            if r:
                tabla = df(r["tabla"])
                st.dataframe(tabla.round(3), width="stretch", hide_index=True)
                if r.get("seleccion", {}).get("elegido"):
                    st.success(f"**Recomendado: {r['seleccion']['elegido']}** — {r['seleccion']['razon']}")
                plot(r["grafico_rmse"], "grp_rmse")
        st.markdown("**Todos los experimentos**")
        st.dataframe(t.round(3), width="stretch", hide_index=True)
    with tab2:
        eid = st.selectbox("Experimento", t["id"].tolist(),
                           format_func=lambda i: f"#{i} · {t.set_index('id').loc[i, 'algoritmo']}")
        _experiment_detail(int(eid))


def gestion() -> None:
    theme.page_header("Gestión de modelos", "Versiones, comparación, aprobación con justificación y publicación para la EPS.")
    st.caption("Ciclo de vida: evaluado → **aprobado** (validación humana con justificación) → **publicado** "
               "(lo consume la EPS) → retirado. Publicar un modelo retira automáticamente el publicado anterior.")
    user = st.session_state["usuario"]
    models = call(api().get, "/models") or []
    if not models:
        st.info("Aún no hay modelos entrenados.")
        return
    rows = []
    for m in models:
        rows.append({"id": m["id"], "estado": f"{ESTADO_ICON.get(m['estado'], '')} {m['estado']}",
                     "modelo": m["nombre"], "RMSE CV": m["metricas"]["rmse_cv_media"],
                     "RMSE prueba": m["metricas"]["rmse_test"], "R² prueba": m["metricas"]["r2_test"],
                     "variables": len(m["variables"] or []), "sintético": m["es_sintetico"],
                     "creado": m["creado"][:16], "publicado": (m["publicado_en"] or "")[:16]})
    st.dataframe(df(rows).round(3), width="stretch", hide_index=True)

    st.subheader("Comparar versiones")
    ids = st.multiselect("Versiones", [m["id"] for m in models], max_selections=6)
    if len(ids) >= 2:
        cmp_ = call(api().get, "/models/compare", ids=ids)
        if cmp_:
            st.dataframe(pd.DataFrame([{"id": m["id"], "nombre": m["nombre"], "estado": m["estado"], **m["metricas"]}
                                       for m in cmp_]).round(3), width="stretch", hide_index=True)

    st.subheader("Acciones sobre una versión")
    mid = st.selectbox("Versión de modelo", [m["id"] for m in models],
                       format_func=lambda i: next(f"#{m['id']} · {m['nombre']} · {m['estado']}" for m in models
                                                  if m["id"] == i))
    m = call(api().get, f"/models/{mid}")
    if not m:
        return
    st.caption(f"Objetivo: `{m['objetivo']}` · Huella: `{m['sha256'][:16]}…` · Experimento #{m['experimento_id']}")
    if m.get("nota_aprobacion"):
        st.info(f"Justificación de aprobación: {m['nota_aprobacion']}")
    if user["rol"] != "admin":
        st.warning("Solo el administrador puede aprobar, publicar o retirar modelos.")
        return
    if m["estado"] == "evaluado":
        with st.form("aprobar"):
            nota = st.text_area("Justificación metodológica de la aprobación (obligatoria)")
            if st.form_submit_button("✅ Aprobar", type="primary"):
                if call(api().post, f"/models/{mid}/approve", {"justificacion": nota}):
                    st.success("Modelo aprobado.")
                    st.rerun()
    if m["estado"] == "aprobado":
        st.warning("Publicar reemplaza el modelo que hoy consulta la EPS y genera las alertas con las reglas activas.")
        if st.button("🚀 Publicar para la API / EPS", type="primary"):
            with st.spinner("Calculando predicciones territoriales fuera de muestra…"):
                r = call(api().post, f"/models/{mid}/publish")
            if r:
                st.success(f"Publicado: {r['predicciones']} predicciones; alertas nuevas: {r['alertas']['creadas']}; "
                           f"retirados: {r['retirados'] or 'ninguno'}")
    if m["estado"] in ("aprobado", "publicado") and st.button("Retirar modelo"):
        if call(api().post, f"/models/{mid}/retire"):
            st.success("Modelo retirado.")
            st.rerun()


def datos_nuevos() -> None:
    theme.page_header("Pruebas con datos nuevos", "Predicción con datos que no participaron en el entrenamiento.")
    st.caption("Aplica automáticamente las transformaciones aprendidas en entrenamiento a datos que no participaron "
               "en él. Si el archivo incluye la variable objetivo, se calculan métricas independientes.")
    models = [m for m in (call(api().get, "/models") or []) if m["estado"] != "retirado"]
    if not models:
        st.info("No hay modelos disponibles.")
        return
    mid = st.selectbox("Modelo", [m["id"] for m in models],
                       format_func=lambda i: next(f"#{m['id']} · {m['nombre']} · {m['estado']}" for m in models
                                                  if m["id"] == i))
    fuente = st.radio("Datos", ["Dataset de validación externa cargado en la plataforma", "Subir archivo"],
                      horizontal=True)
    r = None
    if fuente.startswith("Dataset"):
        ds = [d for d in datasets() if d["rol"] == "externo"] or datasets()
        opts = {f"#{d['id']} · {d['nombre']}": d for d in ds}
        d = opts[st.selectbox("Dataset", list(opts))]
        if st.button("Predecir", type="primary"):
            r = call(api().post, f"/models/{mid}/predict-version/{d['versiones'][-1]['id']}")
    else:
        f = st.file_uploader("Archivo CSV/Excel con las variables del modelo", type=["csv", "xlsx", "xls"])
        if f and st.button("Predecir", type="primary"):
            r = call(api().upload, f"/models/{mid}/predict", f.name, f.getvalue())
    if not r:
        return
    if r.get("territorios_vistos_en_entrenamiento"):
        st.warning(f"{r['territorios_vistos_en_entrenamiento']} territorios del archivo ya participaron en el "
                   "entrenamiento o la prueba del modelo: sus métricas no son independientes.")
    if "metricas" in r:
        c = st.columns(4)
        c[0].metric("MAE", fmt(r["metricas"]["mae"], 2))
        c[1].metric("RMSE", fmt(r["metricas"]["rmse"], 2))
        c[2].metric("R²", fmt(r["metricas"]["r2"], 3))
        c[3].metric("Cobertura del intervalo 90 %", f"{fmt(100 * r['cobertura_intervalo_90'], 1)} %")
        st.caption(f"Calculado sobre {r['n_con_objetivo']} territorios con valor observado.")
    p = df(r["predicciones"])
    st.dataframe(p.round(2), width="stretch", hide_index=True)
    st.download_button("Descargar predicciones (CSV)", p.to_csv(index=False).encode("utf-8-sig"),
                       "predicciones_datos_nuevos.csv", "text/csv")
