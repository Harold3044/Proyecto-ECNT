"""Gráficos Plotly reutilizables por la API y las aplicaciones (se serializan con ``fig.to_json()``)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PALETTE = ["#2563eb", "#f97316", "#16a34a", "#9333ea", "#dc2626", "#0891b2", "#ca8a04", "#64748b"]
_LAYOUT = dict(template="plotly_white", margin=dict(l=40, r=20, t=50, b=40), font=dict(size=12))


def _style(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(title=title, **_LAYOUT)
    return fig


def histogram(df: pd.DataFrame, column: str, nbins: int = 30, color: str | None = None) -> go.Figure:
    fig = px.histogram(df, x=column, nbins=nbins, color=color, marginal="box",
                       color_discrete_sequence=PALETTE)
    return _style(fig, f"Distribución de {column}")


def boxplot_by_group(df: pd.DataFrame, value: str, group: str) -> go.Figure:
    fig = px.box(df, x=group, y=value, points="outliers", color_discrete_sequence=PALETTE)
    return _style(fig, f"{value} por {group}")


def frequency_bar(freq: pd.DataFrame, column: str) -> go.Figure:
    fig = px.bar(freq, x="valor", y="frecuencia", text="porcentaje", color_discrete_sequence=PALETTE)
    fig.update_traces(texttemplate="%{text}%", textposition="outside")
    return _style(fig, f"Frecuencias de {column}")


def correlation_heatmap(corr: pd.DataFrame, title: str = "Matriz de correlación (Spearman)") -> go.Figure:
    fig = px.imshow(corr.round(2), text_auto=True, color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                    aspect="auto")
    fig.update_traces(textfont_size=8)
    return _style(fig, title)


def scatter_vs_target(df: pd.DataFrame, x: str, target: str, color: str | None = None) -> go.Figure:
    fig = px.scatter(df, x=x, y=target, color=color, hover_data=[c for c in ("municipio", "departamento")
                                                                 if c in df.columns],
                     color_discrete_sequence=PALETTE)
    return _style(fig, f"{target} vs {x}")


def missing_bar(df: pd.DataFrame) -> go.Figure:
    pct = (df.isna().mean() * 100).sort_values(ascending=False)
    pct = pct[pct > 0]
    fig = px.bar(x=pct.index, y=pct.values, labels={"x": "variable", "y": "% nulos"},
                 color_discrete_sequence=PALETTE)
    return _style(fig, "Porcentaje de valores nulos por variable")


# --------------------------- Modelado ---------------------------------------
def predicted_vs_actual(y_true, y_pred, labels=None, title: str = "Valores reales vs. predichos") -> go.Figure:
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    lo, hi = float(min(y_true.min(), y_pred.min())), float(max(y_true.max(), y_pred.max()))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=y_true, y=y_pred, mode="markers", text=labels, name="Territorios",
                             marker=dict(color=PALETTE[0], opacity=0.7)))
    fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="Predicción perfecta",
                             line=dict(color=PALETTE[4], dash="dash")))
    fig.update_xaxes(title="Real")
    fig.update_yaxes(title="Predicho")
    return _style(fig, title)


def residuals_plot(y_true, y_pred, labels=None) -> go.Figure:
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    res = y_true - y_pred
    fig = go.Figure(go.Scatter(x=y_pred, y=res, mode="markers", text=labels,
                               marker=dict(color=PALETTE[1], opacity=0.7)))
    fig.add_hline(y=0, line_dash="dash", line_color=PALETTE[7])
    fig.update_xaxes(title="Predicho")
    fig.update_yaxes(title="Residuo (real − predicho)")
    return _style(fig, "Residuos vs. valores predichos")


def residual_histogram(y_true, y_pred) -> go.Figure:
    res = np.asarray(y_true, float) - np.asarray(y_pred, float)
    fig = px.histogram(x=res, nbins=25, labels={"x": "Residuo"}, color_discrete_sequence=PALETTE)
    return _style(fig, "Distribución de los residuos")


def metric_comparison(table: pd.DataFrame, metric: str = "rmse") -> go.Figure:
    """``table`` con columnas modelo, ``<metric>_cv_media``, ``<metric>_cv_de`` y ``<metric>_test``."""
    fig = go.Figure()
    if f"{metric}_cv_media" in table:
        fig.add_trace(go.Bar(x=table["modelo"], y=table[f"{metric}_cv_media"], name="Validación cruzada",
                             error_y=dict(type="data", array=table.get(f"{metric}_cv_de")),
                             marker_color=PALETTE[0]))
    if f"{metric}_test" in table:
        fig.add_trace(go.Bar(x=table["modelo"], y=table[f"{metric}_test"], name="Prueba",
                             marker_color=PALETTE[1]))
    fig.update_layout(barmode="group")
    return _style(fig, f"Comparación de modelos — {metric.upper()}")


def feature_importance_bar(imp: pd.DataFrame, value: str = "importancia", top: int = 15,
                           title: str = "Importancia de variables") -> go.Figure:
    d = imp.sort_values(value, ascending=True).tail(top)
    fig = px.bar(d, x=value, y="variable", orientation="h", error_x=d.get("de"),
                 color_discrete_sequence=PALETTE)
    return _style(fig, title)
