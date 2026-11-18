"""Vistas del ambiente EPS: dashboard, consulta, análisis poblacional, mapa, alertas e informes."""

from __future__ import annotations

import time

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ecnt_client.ui import ESTADO_COLOR, NIVEL_COLOR, PRIORIDAD_COLOR, api, call, df, fmt

NIVELES = ["muy bajo", "bajo", "medio", "alto", "muy alto"]
UNIDAD = "por 100.000 hab."
LAYOUT = dict(template="plotly_white", margin=dict(l=10, r=10, t=50, b=10))


def territories() -> pd.DataFrame:
    """Territorios del modelo publicado con sus determinantes (en caché por sesión durante 2 minutos)."""
    cache = st.session_state.setdefault("_terr_cache", {})
    if "t" in cache and time.time() - cache["ts"] < 120:
        return cache["t"]
    t = df(call(api().get, "/territories", con_determinantes=True))
    cache.update(t=t, ts=time.time())
    return t


META_COLS = {"divipola", "municipio", "departamento", "periodo", "poblacion", "observado", "predicho", "lim_inf",
             "lim_sup", "nivel", "tipo", "lat", "lon"}


def _no_model() -> bool:
    if call(api().get, "/models/published", quiet=True) is None:
        st.warning("Aún no hay un modelo publicado. El administrador debe aprobar y publicar uno.")
        return True
    return False


def _chart(fig, key: str) -> None:
    fig.update_layout(**LAYOUT)
    st.plotly_chart(fig, width="stretch", key=key)


def dashboard() -> None:
    st.title("📊 Dashboard territorial")
    if _no_model():
        return
    d = call(api().get, "/dashboard")
    if not d:
        return
    st.caption(f"Indicador: **{d['objetivo_descripcion']}** ({UNIDAD}). Modelo #{d['modelo']['id']} · "
               f"{d['modelo']['nombre']} · publicado {str(d['modelo']['publicado_en'])[:10]}")
    c = st.columns(5)
    c[0].metric("Territorios analizados", d["total_territorios"])
    c[1].metric("Población total", fmt(d["poblacion_total"], 0))
    c[2].metric("Población rural dispersa y centros poblados", fmt(d["poblacion_rural_dispersa_y_centros_poblados"], 0))
    c[3].metric("Tasa esperada (ponderada)", fmt(d["tasa_esperada_ponderada"]))
    c[4].metric("Alertas abiertas", sum(d["alertas_abiertas"].values()),
                help=", ".join(f"{k}: {v}" for k, v in d["alertas_abiertas"].items()))
    c1, c2 = st.columns(2)
    with c1:
        dist = df(d["distribucion_niveles"])
        fig = px.bar(dist, x="nivel", y="territorios", color="nivel", color_discrete_map=NIVEL_COLOR,
                     title="Distribución territorial del nivel de mortalidad esperada (quintiles)")
        fig.update_layout(showlegend=False)
        _chart(fig, "dist")
    with c2:
        ev = df(d["evolucion"])
        if not ev.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ev.anio, y=ev.tasa_ponderada, name="Tasa ponderada por población",
                                     mode="lines+markers"))
            fig.add_trace(go.Scatter(x=ev.anio, y=ev.tasa_mediana, name="Mediana municipal", mode="lines+markers"))
            fig.add_vrect(x0=2019.5, x1=2021.5, fillcolor="grey", opacity=0.12, line_width=0,
                          annotation_text="pandemia", annotation_position="top left")
            fig.update_layout(title="Evolución de la mortalidad registrada por ECNT (estandarizada)",
                              xaxis=dict(dtick=1), yaxis_title=UNIDAD)
            _chart(fig, "evol")
    c1, c2 = st.columns(2)
    with c1:
        dep = df(d["por_departamento"])
        fig = px.bar(dep, x="predicho_medio", y="departamento", orientation="h",
                     title="Mortalidad esperada media por departamento", labels={"predicho_medio": UNIDAD})
        fig.update_yaxes(categoryorder="total ascending")
        _chart(fig, "dep")
    with c2:
        st.markdown("**Municipios con indicadores más elevados (esperado)**")
        top = df(d["top_territorios"])[["municipio", "departamento", "predicho", "lim_inf", "lim_sup", "observado",
                                        "nivel"]]
        st.dataframe(top.round(1), width="stretch", hide_index=True)
    st.info(d["aviso"])


def _determinants_chart(det: pd.DataFrame, ref: pd.DataFrame | None, title: str) -> go.Figure:
    fig = px.bar(det, x="valor", y="descripcion", orientation="h", title=title, labels={"valor": "", "descripcion": ""})
    if ref is not None:
        fig.add_trace(go.Scatter(x=ref.valor, y=ref.descripcion, mode="markers", name="Mediana del Caribe",
                                 marker=dict(symbol="line-ns", size=18, line_width=3, color="black")))
    fig.update_layout(height=420)
    return fig


def consulta() -> None:
    st.title("📍 Consulta territorial")
    if _no_model():
        return
    t = territories()
    if t.empty:
        return
    c1, c2, c3 = st.columns(3)
    dep = c1.selectbox("Departamento", sorted(t.departamento.unique()))
    sub = t[t.departamento == dep]
    mun = c2.selectbox("Municipio", sorted(sub.municipio))
    c3.selectbox("Periodo", sorted(t.periodo.unique()))
    div = sub[sub.municipio == mun].divipola.iloc[0]
    d = call(api().get, f"/territories/{div}")
    if not d:
        return
    st.subheader(f"{d['municipio']} ({d['departamento']}) · DIVIPOLA {d['divipola']}")
    c = st.columns(5)
    c[0].metric("Nivel", d["nivel"].upper())
    c[1].metric("Mortalidad esperada", fmt(d["predicho"]), help=f"{UNIDAD}; intervalo 90 %")
    c[2].metric("Intervalo 90 %", f"{fmt(d['lim_inf'])} – {fmt(d['lim_sup'])}")
    c[3].metric("Mortalidad registrada", fmt(d["observado"]),
                delta=None if d["observado"] is None else fmt(d["observado"] - d["predicho"]),
                delta_color="inverse")
    c[4].metric("Población 2018", fmt(d["poblacion"], 0))
    if d["observado"] is not None and d["observado"] < d["lim_inf"]:
        st.warning("La mortalidad registrada está por debajo de lo esperado: posible **subregistro** o baja "
                   "certificación médica de la causa. No debe interpretarse como menor riesgo.")
    if d["observado"] is not None and d["observado"] > d["lim_sup"]:
        st.warning("La mortalidad registrada **supera** el intervalo esperado: amerita revisión epidemiológica.",
                   icon="🔺")
    c1, c2 = st.columns(2)
    det = df(d["determinantes"])
    with c1:
        if not det.empty:
            det["mediana_caribe"] = [t[v].median() if v in t else None for v in det.variable]
            pct = det[det.unidad == "%"]
            ref = pct[["descripcion", "mediana_caribe"]].rename(columns={"mediana_caribe": "valor"})
            _chart(_determinants_chart(pct, ref, "Determinantes sociales (%) frente a la mediana del Caribe"), "det")
            st.dataframe(det[["descripcion", "valor", "mediana_caribe", "unidad"]].round(2), width="stretch",
                         hide_index=True)
    with c2:
        h = df(d["historial"])
        if not h.empty:
            fig = px.line(h, x="anio", y="tasa_ecnt_std", markers=True,
                          title="Mortalidad registrada por ECNT (estandarizada) por año",
                          labels={"tasa_ecnt_std": UNIDAD, "anio": "Año"})
            fig.add_hline(y=d["predicho"], line_dash="dash", annotation_text="esperado por el modelo")
            fig.update_xaxes(dtick=1)
            _chart(fig, "hist")
            show = h[["anio", "tasa_ecnt_std", "defunciones_ecnt", "poblacion"]].copy()
            show["defunciones_ecnt"] = [("< 10 (suprimido)" if s else fmt(n, 0)) for n, s in
                                        zip(h.defunciones_ecnt, h.conteo_suprimido, strict=True)]
            st.dataframe(show.round(1), width="stretch", hide_index=True)
    if d["alertas"]:
        st.markdown("**Alertas del territorio**")
        st.dataframe(df(d["alertas"]), width="stretch", hide_index=True)
    st.caption(d["aviso"])


def analisis() -> None:
    st.title("⚖️ Análisis poblacional comparativo")
    if _no_model():
        return
    t = territories()
    if t.empty:
        return
    tab1, tab2, tab3 = st.tabs(["Municipios", "Departamentos", "Determinantes vs. riesgo"])
    with tab1:
        opts = {f"{r.municipio} ({r.departamento})": r.divipola for r in t.itertuples()}
        default = list(opts)[:4]
        sel = st.multiselect("Municipios a comparar (2 a 10)", list(opts), default=default, max_selections=10)
        if len(sel) >= 2:
            cmp_ = df(call(api().get, "/territories/compare", ids=[opts[s] for s in sel]))
            if not cmp_.empty:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=cmp_.municipio, y=cmp_.predicho, name="Esperado",
                                     error_y=dict(type="data", symmetric=False, array=cmp_.lim_sup - cmp_.predicho,
                                                  arrayminus=cmp_.predicho - cmp_.lim_inf)))
                fig.add_trace(go.Scatter(x=cmp_.municipio, y=cmp_.observado, mode="markers", name="Registrado",
                                         marker=dict(size=12, symbol="diamond", color="black")))
                fig.update_layout(title=f"Mortalidad por ECNT esperada (IC 90 %) y registrada · {UNIDAD}")
                _chart(fig, "cmpm")
                st.dataframe(cmp_.round(2), width="stretch", hide_index=True)
    with tab2:
        fig = px.box(t, x="departamento", y="predicho", points="all", hover_name="municipio",
                     title=f"Mortalidad esperada por departamento ({UNIDAD})")
        _chart(fig, "boxdep")
        agg = t.groupby("departamento").agg(territorios=("divipola", "count"), poblacion=("poblacion", "sum"),
                                            esperado_medio=("predicho", "mean"), registrado_medio=("observado", "mean"))
        st.dataframe(agg.round(1), width="stretch")
    with tab3:
        variables = [c for c in t.columns if c not in META_COLS]
        if variables:
            c1, c2 = st.columns(2)
            var = c1.selectbox("Determinante", variables)
            y = c2.selectbox("Indicador", ["predicho", "observado"],
                             format_func={"predicho": "Mortalidad esperada", "observado": "Mortalidad registrada"}.get)
            fig = px.scatter(t, x=var, y=y, color="nivel", color_discrete_map=NIVEL_COLOR, hover_name="municipio",
                             category_orders={"nivel": NIVELES}, title=f"{var} vs. {y}", labels={y: UNIDAD})
            _chart(fig, "scat")
            st.caption("Asociación estadística entre territorios; no implica causalidad.")


def mapa() -> None:
    st.title("🗺️ Mapa territorial")
    if _no_model():
        return
    t = territories()
    if t.empty or "lat" not in t or t.lat.isna().all():
        st.info("No hay coordenadas disponibles para los territorios.")
        return
    c1, c2 = st.columns(2)
    var = c1.selectbox("Indicador", ["predicho", "observado", "nivel"],
                       format_func={"predicho": "Mortalidad esperada", "observado": "Mortalidad registrada",
                                    "nivel": "Nivel (quintil)"}.get)
    deps = c2.multiselect("Departamentos", sorted(t.departamento.unique()))
    m = t[t.departamento.isin(deps)] if deps else t
    m = m.dropna(subset=["lat", "lon"]).copy()
    m["tamano"] = m.poblacion.fillna(0).clip(lower=5000) ** 0.5
    kw = dict(lat="lat", lon="lon", size="tamano", size_max=28, hover_name="municipio", zoom=6, height=650,
              hover_data={"departamento": True, "predicho": ":.1f", "observado": ":.1f", "nivel": True,
                          "poblacion": ":,.0f", "lat": False, "lon": False, "tamano": False})
    if var == "nivel":
        fig = px.scatter_map(m, color="nivel", color_discrete_map=NIVEL_COLOR, category_orders={"nivel": NIVELES},
                             **kw)
    else:
        fig = px.scatter_map(m, color=var, color_continuous_scale="YlOrRd", **kw)
    fig.update_layout(map_style="open-street-map", margin=dict(l=0, r=0, t=30, b=0),
                      title="Cabeceras municipales · tamaño proporcional a la población")
    st.plotly_chart(fig, width="stretch", key="map")
    st.caption("Ubicación: cabecera municipal (DIVIPOLA, DANE). Tamaño ∝ √población. Mapa base © OpenStreetMap.")


def alertas() -> None:
    st.title("🚨 Alertas poblacionales")
    st.caption("Apoyan la priorización de acciones preventivas y de salud pública. No son diagnósticos.")
    cat = call(api().get, "/catalog/alerts") or {}
    c1, c2, c3 = st.columns(3)
    estado = c1.selectbox("Estado", ["(todos)", *cat.get("estados", [])])
    prioridad = c2.selectbox("Prioridad", ["(todas)", *cat.get("prioridades", [])])
    t = territories()
    dep = c3.selectbox("Departamento", ["(todos)", *sorted(t.departamento.unique())] if not t.empty else ["(todos)"])
    al = df(call(api().get, "/alerts", estado=None if estado.startswith("(") else estado,
                 prioridad=None if prioridad.startswith("(") else prioridad,
                 departamento=None if dep.startswith("(") else dep))
    if al.empty:
        st.info("No hay alertas con esos filtros.")
        return
    k = st.columns(4)
    k[0].metric("Alertas", len(al))
    k[1].metric("Prioridad alta", int((al.prioridad == "alta").sum()))
    k[2].metric("Sin responsable", int(al.responsable.isna().sum()))
    k[3].metric("Abiertas", int((~al.estado.isin(["cerrada", "descartada"])).sum()))
    view = al.assign(estado=al.estado.map(lambda s: f"{ESTADO_COLOR.get(s, '')} {s}"),
                     prioridad=al.prioridad.map(lambda p: f"{PRIORIDAD_COLOR.get(p, '')} {p}"))
    st.dataframe(view[["id", "prioridad", "estado", "municipio", "departamento", "regla", "detalle", "responsable",
                       "actualizado"]], width="stretch", hide_index=True)

    st.subheader("Seguimiento")
    aid = st.selectbox("Alerta", al.id.tolist(), format_func=lambda i: f"#{i} · " + al.set_index("id").loc[i, "titulo"])
    a = call(api().get, f"/alerts/{aid}")
    if not a:
        return
    c1, c2 = st.columns([2, 3])
    with c1:
        st.markdown(f"**{a['titulo']}**  \n{a['detalle']}  \nEstado: **{a['estado']}** · Prioridad: "
                    f"**{a['prioridad']}** · Responsable: **{a['responsable'] or '—'}**")
        with st.form(f"upd_{aid}"):
            nuevo = st.selectbox("Cambiar estado", ["(sin cambio)", *a["transiciones_permitidas"]])
            prio = st.selectbox("Prioridad", ["(sin cambio)", "alta", "media", "baja"])
            resp = st.text_input("Responsable", value=a["responsable"] or "")
            obs = st.text_area("Observación")
            if st.form_submit_button("Registrar", type="primary"):
                body = {"estado": None if nuevo.startswith("(") else nuevo,
                        "prioridad": None if prio.startswith("(") else prio,
                        "responsable": resp if resp and resp != (a["responsable"] or "") else None,
                        "observacion": obs or None}
                if call(api().patch, f"/alerts/{aid}", body):
                    st.success("Cambios registrados.")
                    st.rerun()
    with c2:
        st.markdown("**Historial**")
        hist = df(a["historial"])
        if not hist.empty:
            st.dataframe(hist[["creado", "tipo", "valor_anterior", "valor_nuevo", "observacion"]], width="stretch",
                         hide_index=True)
        st.markdown("**Evidencia**")
        st.json(a["evidencia"])


def informes() -> None:
    st.title("📄 Exportar informes")
    if _no_model():
        return
    t = territories()
    dep = st.selectbox("Departamento", ["(todos)", *sorted(t.departamento.unique())])
    if st.button("Preparar informe territorial (CSV)"):
        content = call(api().download, "/territories/export", departamento=None if dep.startswith("(") else dep)
        if content:
            st.download_button("Descargar informe territorial", content, "informe_territorial.csv", "text/csv")
    al = df(call(api().get, "/alerts", departamento=None if dep.startswith("(") else dep))
    if not al.empty:
        st.download_button("Descargar alertas (CSV)", al.drop(columns=["evidencia", "transiciones_permitidas"],
                                                               errors="ignore").to_csv(index=False).encode("utf-8-sig"),
                           "alertas.csv", "text/csv")
    st.caption("Los informes contienen solo información territorial agregada.")
