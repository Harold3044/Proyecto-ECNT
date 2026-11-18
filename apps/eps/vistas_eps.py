"""Vistas del ambiente EPS (diseño basado en ecnt-frontend): panel principal, directorio territorial,
análisis poblacional, mapa, centro de alertas, informes y diccionario de variables.

Nota: el diseño original tenía un "Directorio de Pacientes"; aquí es un **Directorio de Territorios**
porque el proyecto trabaja con unidades territoriales agregadas, nunca con personas.
"""

from __future__ import annotations

import time

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ecnt_client import theme
from ecnt_client.ui import api, call, df, fmt, variable_dictionary

NIVELES = ["muy bajo", "bajo", "medio", "alto", "muy alto"]
UNIDAD = "por 100.000 hab."
META_COLS = {"divipola", "municipio", "departamento", "periodo", "poblacion", "observado", "predicho", "lim_inf",
             "lim_sup", "nivel", "tipo", "lat", "lon"}


def territories() -> pd.DataFrame:
    """Territorios del modelo publicado con sus determinantes (caché por sesión durante 2 minutos)."""
    cache = st.session_state.setdefault("_terr_cache", {})
    if "t" in cache and time.time() - cache["ts"] < 120:
        return cache["t"]
    t = df(call(api().get, "/territories", con_determinantes=True))
    cache.update(t=t, ts=time.time())
    return t


def _dictionary() -> dict[str, dict]:
    cache = st.session_state.setdefault("_dic_cache", {})
    if not cache:
        cat = call(api().get, "/catalog/variables", quiet=True) or {}
        for s in cat.get("variables", []) + cat.get("panel", []) + cat.get("resultados", []):
            cache[s["name"]] = s
    return cache


def label(var: str) -> str:
    s = _dictionary().get(var)
    return f"{s['description']} ({s['unit']})" if s and s.get("unit") else (s["description"] if s else var)


def _no_model() -> bool:
    if call(api().get, "/models/published", quiet=True) is None:
        theme.notice("<strong>Aún no hay un modelo publicado.</strong> El administrador debe aprobar y publicar uno.",
                     "warning", "info")
        return True
    return False


def _chart(fig, key: str, height: int | None = None) -> None:
    st.plotly_chart(theme.style_fig(fig, height), width="stretch", key=key)


# ------------------------------------------------------------------------------------------
def dashboard() -> None:
    theme.page_header("Panel de control poblacional", "Resumen del riesgo territorial de ECNT en el Caribe "
                      "colombiano según los determinantes sociales.")
    if _no_model():
        return
    d = call(api().get, "/dashboard")
    t = territories()
    if not d:
        return
    altos = int(t.nivel.isin(["alto", "muy alto"]).sum()) if not t.empty else 0
    theme.stat_cards([
        ("map", "blue", "Territorios analizados", d["total_territorios"], "Municipios del Caribe"),
        ("alert", "red", "Riesgo alto o muy alto", altos, "Municipios en los dos quintiles superiores"),
        ("trending", "orange", "Alertas activas", sum(d["alertas_abiertas"].values()),
         ", ".join(f"{k}: {v}" for k, v in d["alertas_abiertas"].items()) or "Sin alertas"),
        ("users", "green", "Población rural dispersa y centros poblados",
         fmt(d["poblacion_rural_dispersa_y_centros_poblados"], 0), f"de {fmt(d['poblacion_total'], 0)} habitantes"),
    ])
    st.caption(f"Indicador: **{d['objetivo_descripcion']}** ({UNIDAD}). Tasa esperada ponderada por población: "
               f"**{fmt(d['tasa_esperada_ponderada'])}**. Modelo #{d['modelo']['id']} · {d['modelo']['nombre']}.")
    c1, c2 = st.columns(2)
    with c1, theme.card("Distribución por nivel de riesgo", "Municipios por quintil de mortalidad esperada"):
        dist = df(d["distribucion_niveles"])
        fig = go.Figure(go.Pie(labels=dist.nivel, values=dist.territorios, hole=0.55, sort=False,
                               marker=dict(colors=[theme.RISK[n] for n in dist.nivel]), textinfo="value"))
        _chart(fig, "pie", 320)
    with c2, theme.card("Riesgo por departamento", "Número de municipios por nivel"):
        if not t.empty:
            g = t.groupby(["departamento", "nivel"]).size().reset_index(name="municipios")
            fig = px.bar(g, y="departamento", x="municipios", color="nivel", orientation="h",
                         color_discrete_map=theme.RISK, category_orders={"nivel": NIVELES[::-1]})
            fig.update_layout(barmode="stack", yaxis_title="", xaxis_title="", legend_title="")
            _chart(fig, "depbar", 320)
    c1, c2 = st.columns([3, 2])
    with c1, theme.card("Evolución de la mortalidad registrada por ECNT", "Tasa estandarizada por edad, 2018–2021"):
        ev = df(d["evolucion"])
        if not ev.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ev.anio, y=ev.tasa_ponderada, name="Ponderada por población",
                                     mode="lines+markers", line=dict(color=theme.ENV["eps"]["primary"], width=3)))
            fig.add_trace(go.Scatter(x=ev.anio, y=ev.tasa_mediana, name="Mediana municipal", mode="lines+markers",
                                     line=dict(color="#E0A72E", dash="dot")))
            fig.add_vrect(x0=2019.5, x1=2021.5, fillcolor="#94A3B8", opacity=0.12, line_width=0,
                          annotation_text="pandemia", annotation_position="top left")
            fig.update_layout(xaxis=dict(dtick=1), yaxis_title=UNIDAD)
            _chart(fig, "evol", 300)
    with c2, theme.card("Municipios con mayor riesgo esperado"):
        top = df(d["top_territorios"])
        rows = [[f"<b>{theme.esc(r.municipio)}</b><br><span class='ecnt-muted'>{theme.esc(r.departamento)}</span>",
                 theme.badge(r.nivel, theme.RISK[r.nivel]), fmt(r.predicho)] for r in top.itertuples()]
        theme.html_table(["Municipio", "Nivel", "Esperado"], rows)
    if not t.empty:
        share = (t.assign(a=t.nivel.isin(["alto", "muy alto"])).groupby("departamento").a.mean()
                 .sort_values(ascending=False))
        top2 = [f"<strong>{theme.esc(x.title())}</strong> ({share[x]:.0%})" for x in share.index[:2]]
        theme.notice(f"<strong>Análisis geográfico:</strong> los departamentos con mayor proporción de municipios en "
                     f"riesgo alto o muy alto son {' y '.join(top2)}. Se recomienda priorizar allí las acciones "
                     "preventivas, verificando también los municipios con posible subregistro.", "success", "map")
    theme.notice(d["aviso"], "warning", "shield")


# ------------------------------------------------------------------------------------------
def consulta() -> None:
    theme.page_header("Directorio de territorios", "Municipios priorizados por nivel de mortalidad esperada por "
                      "ECNT. Seleccione uno para ver su ficha.")
    if _no_model():
        return
    t = territories()
    if t.empty:
        return
    c1, c2, c3 = st.columns([2, 1.2, 2.2])
    q = c1.text_input("Buscar", placeholder="Buscar por municipio o código DIVIPOLA…", label_visibility="collapsed")
    dep = c2.selectbox("Departamento", ["Todos", *sorted(t.departamento.unique())], label_visibility="collapsed")
    nivel = c3.segmented_control("Nivel", ["Todos", *NIVELES[::-1]], default="Todos", label_visibility="collapsed")
    f = t.copy()
    if q:
        f = f[f.municipio.str.lower().str.contains(q.lower()) | f.divipola.str.contains(q)]
    if dep != "Todos":
        f = f[f.departamento == dep]
    if nivel and nivel != "Todos":
        f = f[f.nivel == nivel]
    f = f.sort_values("predicho", ascending=False)
    vmax = float(t.predicho.max())
    rows = []
    for r in f.head(60).itertuples():
        color = theme.RISK[r.nivel]
        obs = "—" if pd.isna(r.observado) else fmt(r.observado)
        flag = ""
        if not pd.isna(r.observado) and r.observado < r.lim_inf:
            flag = theme.badge("posible subregistro", "#7E22CE")
        elif not pd.isna(r.observado) and r.observado > r.lim_sup:
            flag = theme.badge("exceso", "#B91C1C")
        rows.append([f"<b>{theme.esc(r.municipio)}</b><br><span class='ecnt-muted'>DIVIPOLA {r.divipola}</span>",
                     theme.esc(r.departamento.title()), fmt(r.poblacion, 0), theme.badge(r.nivel, color),
                     theme.bar(r.predicho, vmax, color, fmt(r.predicho)), obs, flag])
    theme.html_table(["Municipio", "Departamento", "Población", "Nivel", "Mortalidad esperada", "Registrada",
                      "Observación"], rows)
    st.caption(f"{len(f)} municipios encontrados (se muestran hasta 60). Mortalidad {UNIDAD}, ajustada por edad.")

    opts = {f"{r.municipio} ({r.departamento.title()})": r.divipola for r in f.itertuples()}
    if not opts:
        st.info("No se encontraron territorios con los filtros seleccionados.")
        return
    theme.section("Ficha territorial")
    sel = st.selectbox("Municipio", list(opts))
    d = call(api().get, f"/territories/{opts[sel]}")
    if not d:
        return
    color = theme.RISK[d["nivel"]]
    theme.stat_cards([
        ("activity", "red" if d["nivel"] in ("alto", "muy alto") else "green", "Nivel de riesgo esperado",
         d["nivel"].upper(), "Quintil dentro del Caribe"),
        ("trending", "blue", "Mortalidad esperada", fmt(d["predicho"]),
         f"Intervalo 90 %: {fmt(d['lim_inf'])} – {fmt(d['lim_sup'])}"),
        ("chart", "purple", "Mortalidad registrada", fmt(d["observado"]), f"{UNIDAD} · DANE 2018-2019"),
        ("users", "orange", "Población 2018", fmt(d["poblacion"], 0), d["departamento"].title()),
    ])
    if d["observado"] is not None and d["observado"] < d["lim_inf"]:
        theme.notice("<strong>Posible subregistro:</strong> la mortalidad registrada está por debajo de lo esperado. "
                     "Puede reflejar baja certificación médica de la causa o dificultades de acceso; no debe "
                     "interpretarse como menor riesgo.", "info", "info")
    if d["observado"] is not None and d["observado"] > d["lim_sup"]:
        theme.notice("<strong>Exceso de mortalidad:</strong> lo registrado supera el intervalo esperado; amerita "
                     "revisión epidemiológica.", "danger", "alert")
    det = df(d["determinantes"])
    c1, c2 = st.columns(2)
    with c1, theme.card("Determinantes sociales", "Valor del municipio frente a la mediana del Caribe"):
        if not det.empty:
            det["mediana_caribe"] = [t[v].median() if v in t else None for v in det.variable]
            pct = det[det.unidad == "%"]
            fig = go.Figure()
            fig.add_trace(go.Bar(y=pct.descripcion, x=pct.valor, orientation="h", name=d["municipio"].title(),
                                 marker_color=color))
            fig.add_trace(go.Scatter(y=pct.descripcion, x=pct.mediana_caribe, mode="markers", name="Mediana Caribe",
                                     marker=dict(symbol="line-ns", size=18, line_width=3, color="#0F172A")))
            fig.update_layout(xaxis_title="%")
            _chart(fig, "det", 420)
    with c2, theme.card("Evolución de la mortalidad registrada", "Tasa anual estandarizada por edad"):
        h = df(d["historial"])
        if not h.empty:
            fig = px.line(h, x="anio", y="tasa_ecnt_std", markers=True, labels={"tasa_ecnt_std": UNIDAD, "anio": ""})
            fig.update_traces(line=dict(color=theme.ENV["eps"]["primary"], width=3))
            fig.add_hline(y=d["predicho"], line_dash="dash", line_color=color, annotation_text="esperado por el modelo")
            fig.update_xaxes(dtick=1)
            _chart(fig, "hist", 260)
            show = h[["anio", "tasa_ecnt_std", "defunciones_ecnt", "poblacion"]].copy()
            show["defunciones_ecnt"] = [("< 10 (suprimido)" if s else fmt(n, 0)) for n, s in
                                        zip(h.defunciones_ecnt, h.conteo_suprimido, strict=True)]
            st.dataframe(show.rename(columns={"anio": "año", "tasa_ecnt_std": f"tasa ({UNIDAD})",
                                              "defunciones_ecnt": "defunciones ECNT", "poblacion": "población"})
                         .round(1), width="stretch", hide_index=True)
    with theme.card("Detalle de los determinantes"):
        st.dataframe(det[["descripcion", "valor", "mediana_caribe", "unidad", "explicacion"]].rename(columns={
            "descripcion": "variable", "mediana_caribe": "mediana Caribe", "explicacion": "qué significa"}).round(2),
            width="stretch", hide_index=True, column_config={"qué significa": st.column_config.TextColumn(width="large")})
    if d["alertas"]:
        theme.section("Alertas del territorio")
        for a in d["alertas"]:
            st.markdown(f"• **#{a['id']}** {a['titulo']} — {a['estado']} (prioridad {a['prioridad']})")
    st.caption(d["aviso"])


# ------------------------------------------------------------------------------------------
def analisis() -> None:
    theme.page_header("Análisis poblacional comparativo", "Compare municipios, departamentos y la relación entre "
                      "determinantes sociales y mortalidad.")
    if _no_model():
        return
    t = territories()
    if t.empty:
        return
    tab1, tab2, tab3 = st.tabs(["Municipios", "Departamentos", "Determinantes vs. riesgo"])
    with tab1:
        opts = {f"{r.municipio} ({r.departamento.title()})": r.divipola for r in t.itertuples()}
        sel = st.multiselect("Municipios a comparar (2 a 10)", list(opts), default=list(opts)[:4], max_selections=10)
        if len(sel) >= 2:
            cmp_ = df(call(api().get, "/territories/compare", ids=[opts[s] for s in sel]))
            if not cmp_.empty:
                with theme.card("Mortalidad esperada (intervalo 90 %) y registrada", UNIDAD):
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=cmp_.municipio, y=cmp_.predicho, name="Esperada",
                                         marker_color=[theme.RISK[n] for n in cmp_.nivel],
                                         error_y=dict(type="data", symmetric=False,
                                                      array=cmp_.lim_sup - cmp_.predicho,
                                                      arrayminus=cmp_.predicho - cmp_.lim_inf)))
                    fig.add_trace(go.Scatter(x=cmp_.municipio, y=cmp_.observado, mode="markers", name="Registrada",
                                             marker=dict(size=12, symbol="diamond", color="#0F172A")))
                    _chart(fig, "cmpm", 380)
                show = cmp_.rename(columns={c: label(c) for c in cmp_.columns if c not in ("municipio",)})
                st.dataframe(show.round(2), width="stretch", hide_index=True)
    with tab2:
        with theme.card("Mortalidad esperada por departamento", UNIDAD):
            fig = px.box(t, x="departamento", y="predicho", points="all", hover_name="municipio",
                         color_discrete_sequence=[theme.ENV["eps"]["primary"]], labels={"predicho": UNIDAD})
            _chart(fig, "boxdep", 380)
        agg = t.groupby("departamento").agg(territorios=("divipola", "count"), poblacion=("poblacion", "sum"),
                                            esperado_medio=("predicho", "mean"), registrado_medio=("observado", "mean"))
        st.dataframe(agg.round(1), width="stretch")
    with tab3:
        variables = [c for c in t.columns if c not in META_COLS]
        if variables:
            c1, c2 = st.columns(2)
            var = c1.selectbox("Determinante", variables, format_func=label)
            y = c2.selectbox("Indicador", ["predicho", "observado"],
                             format_func={"predicho": "Mortalidad esperada", "observado": "Mortalidad registrada"}.get)
            info = _dictionary().get(var)
            if info:
                theme.notice(f"<strong>{theme.esc(info['description'])}:</strong> {theme.esc(info['explicacion'])}",
                             "info", "info")
            with theme.card(f"{label(var)} vs. {'mortalidad esperada' if y == 'predicho' else 'mortalidad registrada'}"):
                fig = px.scatter(t, x=var, y=y, color="nivel", color_discrete_map=theme.RISK, hover_name="municipio",
                                 category_orders={"nivel": NIVELES}, labels={y: UNIDAD, var: label(var)})
                _chart(fig, "scat", 420)
            st.caption("Asociación estadística entre territorios; no implica causalidad.")


# ------------------------------------------------------------------------------------------
def mapa() -> None:
    theme.page_header("Mapa territorial", "Cabeceras municipales; el tamaño es proporcional a la población.")
    if _no_model():
        return
    t = territories()
    if t.empty or "lat" not in t or t.lat.isna().all():
        st.info("No hay coordenadas disponibles para los territorios.")
        return
    c1, c2 = st.columns(2)
    var = c1.selectbox("Indicador", ["nivel", "predicho", "observado"],
                       format_func={"predicho": "Mortalidad esperada", "observado": "Mortalidad registrada",
                                    "nivel": "Nivel de riesgo (quintil)"}.get)
    deps = c2.multiselect("Departamentos", sorted(t.departamento.unique()))
    m = t[t.departamento.isin(deps)] if deps else t
    m = m.dropna(subset=["lat", "lon"]).copy()
    m["tamano"] = m.poblacion.fillna(0).clip(lower=5000) ** 0.5
    kw = dict(lat="lat", lon="lon", size="tamano", size_max=28, hover_name="municipio", zoom=6, height=640,
              hover_data={"departamento": True, "predicho": ":.1f", "observado": ":.1f", "nivel": True,
                          "poblacion": ":,.0f", "lat": False, "lon": False, "tamano": False})
    if var == "nivel":
        fig = px.scatter_map(m, color="nivel", color_discrete_map=theme.RISK, category_orders={"nivel": NIVELES}, **kw)
    else:
        fig = px.scatter_map(m, color=var, color_continuous_scale="YlOrRd", **kw)
    fig.update_layout(map_style="open-street-map", margin=dict(l=0, r=0, t=0, b=0))
    with theme.card():
        st.plotly_chart(fig, width="stretch", key="map")
    st.caption("Ubicación: cabecera municipal (DIVIPOLA, DANE). Tamaño ∝ √población. Mapa base © OpenStreetMap.")


# ------------------------------------------------------------------------------------------
def alertas() -> None:
    cat = call(api().get, "/catalog/alerts") or {}
    todas = df(call(api().get, "/alerts"))
    abiertas = 0 if todas.empty else int((~todas.estado.isin(["cerrada", "descartada"])).sum())
    theme.page_header("Centro de alertas", "Seguimiento y priorización de territorios. Las alertas apoyan acciones "
                      "preventivas; no son diagnósticos.", right=f"{theme.icon('alert', 16)} <b>{abiertas}</b> "
                      "alertas activas")
    if todas.empty:
        st.info("No hay alertas.")
        return
    c1, c2, c3 = st.columns([2, 1.4, 1.4])
    prioridad = c1.segmented_control("Prioridad", ["Todas", "alta", "media", "baja"], default="Todas")
    estado = c2.selectbox("Estado", ["(todos)", *cat.get("estados", [])])
    dep = c3.selectbox("Departamento", ["(todos)", *sorted(todas.departamento.unique())])
    al = todas
    if prioridad and prioridad != "Todas":
        al = al[al.prioridad == prioridad]
    if not estado.startswith("("):
        al = al[al.estado == estado]
    if not dep.startswith("("):
        al = al[al.departamento == dep]
    theme.stat_cards([
        ("alert", "red", "Prioridad alta", int((al.prioridad == "alta").sum()), "En la selección"),
        ("clock", "orange", "Sin responsable", int(al.responsable.isna().sum()), "Requieren asignación"),
        ("check", "green", "Cerradas", int((al.estado == "cerrada").sum()), "Con seguimiento completo"),
    ])
    if al.empty:
        st.info("No hay alertas con esos filtros.")
        return
    left, right = st.columns([1.15, 1])
    with left:
        theme.section("Alertas", f"{len(al)} en la selección (se muestran las 30 más recientes)")
        for a in al.head(30).to_dict("records"):
            theme.alert_card(a)
    with right:
        theme.section("Seguimiento", "Cambie el estado, la prioridad o el responsable y registre observaciones")
        aid = st.selectbox("Alerta", al.id.tolist(),
                           format_func=lambda i: f"#{i} · " + al.set_index("id").loc[i, "titulo"])
        a = call(api().get, f"/alerts/{aid}")
        if not a:
            return
        theme.alert_card(a)
        with st.form(f"upd_{aid}"):
            nuevo = st.selectbox("Cambiar estado", ["(sin cambio)", *a["transiciones_permitidas"]])
            prio = st.selectbox("Prioridad", ["(sin cambio)", "alta", "media", "baja"])
            resp = st.text_input("Responsable", value=a["responsable"] or "")
            obs = st.text_area("Observación")
            if st.form_submit_button("Registrar", type="primary", width="stretch"):
                body = {"estado": None if nuevo.startswith("(") else nuevo,
                        "prioridad": None if prio.startswith("(") else prio,
                        "responsable": resp if resp and resp != (a["responsable"] or "") else None,
                        "observacion": obs or None}
                if call(api().patch, f"/alerts/{aid}", body):
                    st.success("Cambios registrados.")
                    st.rerun()
        hist = df(a["historial"])
        if not hist.empty:
            st.markdown("**Historial**")
            st.dataframe(hist[["creado", "tipo", "valor_anterior", "valor_nuevo", "observacion"]].rename(
                columns={"creado": "fecha", "valor_anterior": "antes", "valor_nuevo": "después"}),
                width="stretch", hide_index=True)
        with st.expander("Evidencia que originó la alerta"):
            st.json(a["evidencia"])


# ------------------------------------------------------------------------------------------
def informes() -> None:
    theme.page_header("Exportar informes", "Descargue la información territorial agregada y las alertas en CSV.")
    if _no_model():
        return
    t = territories()
    dep = st.selectbox("Departamento", ["(todos)", *sorted(t.departamento.unique())])
    c1, c2 = st.columns(2)
    with c1:
        theme.action_card("file", "blue", "Informe territorial", "Nivel, mortalidad esperada e intervalo, mortalidad "
                          "registrada y población de cada municipio.")
        if st.button("Preparar informe territorial", width="stretch"):
            content = call(api().download, "/territories/export", departamento=None if dep.startswith("(") else dep)
            if content:
                st.download_button("⬇ Descargar informe territorial (CSV)", content, "informe_territorial.csv",
                                   "text/csv", width="stretch")
    with c2:
        theme.action_card("alert", "orange", "Alertas", "Listado de alertas con prioridad, estado, responsable y "
                          "detalle.")
        al = df(call(api().get, "/alerts", departamento=None if dep.startswith("(") else dep))
        if not al.empty:
            st.download_button("⬇ Descargar alertas (CSV)", al.drop(columns=["evidencia", "transiciones_permitidas"],
                                                                    errors="ignore").to_csv(index=False)
                               .encode("utf-8-sig"), "alertas.csv", "text/csv", width="stretch")
    theme.notice("Los informes contienen solo información territorial agregada (sin datos personales).", "success",
                 "shield")


def diccionario() -> None:
    theme.page_header("Diccionario de variables", "Qué significa cada variable que muestra la plataforma.")
    cat = call(api().get, "/catalog/variables") or {}
    theme.notice("Cada fila de los datos es un <strong>municipio</strong>, no una persona. Los indicadores NBI son "
                 "porcentajes de personas que viven en hogares con esa carencia, y se publican para tres áreas: "
                 "<code>_total</code> (todo el municipio), <code>_cab</code> (cabecera urbana) y <code>_resto</code> "
                 "(centros poblados y zona rural dispersa).", "info", "info")
    rows = [{"variable": s["name"], "descripcion": s["description"], "unidad": s["unit"], "grupo": s["grupo"],
             "explicacion": s["explicacion"]} for s in cat.get("resultados", []) + cat.get("variables", [])]
    variable_dictionary(rows, "eps_dic", "Ver el diccionario completo")
    theme.section("Variables más importantes para la EPS")
    for name in ("predicho", "observado", "lim_inf", "nivel", "tasa_mort_ecnt_std", "pct_poblacion_resto",
                 "comp_servicios_resto", "comp_inasistencia_resto", "nbi_resto"):
        s = _dictionary().get(name)
        if s:
            with st.container(border=True):
                st.markdown(f"**{s['description']}** · `{name}`" + (f" · {s['unit']}" if s["unit"] else ""))
                st.caption(s["explicacion"])
