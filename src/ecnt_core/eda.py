"""Análisis exploratorio: estadística descriptiva, frecuencias, calidad, atípicos y correlaciones."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ecnt_core.schemas import CANONICAL, DEFAULT_KEY
from ecnt_core.validation import validate


def numeric_columns(df: pd.DataFrame, exclude: set[str] | None = None) -> list[str]:
    exclude = exclude or set()
    out = []
    for c in df.columns:
        spec = CANONICAL.get(c)
        if c in exclude or (spec is not None and spec.kind in ("id", "meta", "categorical")):
            continue
        if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c]):
            out.append(c)
    return out


def categorical_columns(df: pd.DataFrame, max_levels: int = 50) -> list[str]:
    out = []
    for c in df.columns:
        if c in numeric_columns(df) or c == "divipola":
            continue
        if df[c].nunique(dropna=True) <= max_levels:
            out.append(c)
    return out


def iqr_outlier_mask(s: pd.Series, k: float = 1.5) -> pd.Series:
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    return (s < q1 - k * iqr) | (s > q3 + k * iqr)


def numeric_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Media, mediana, moda, desviación estándar, mínimos, máximos, cuartiles, forma y atípicos."""
    rows = []
    for c in numeric_columns(df):
        s = pd.to_numeric(df[c], errors="coerce")
        valid = s.dropna()
        mode = valid.mode()
        rows.append({
            "variable": c,
            "n": int(valid.size),
            "nulos": int(s.isna().sum()),
            "pct_nulos": round(float(s.isna().mean() * 100), 2),
            "media": valid.mean(),
            "mediana": valid.median(),
            "moda": mode.iloc[0] if len(mode) and len(mode) < len(valid) else np.nan,
            "desv_estandar": valid.std(),
            "minimo": valid.min(),
            "q1": valid.quantile(0.25),
            "q3": valid.quantile(0.75),
            "maximo": valid.max(),
            "asimetria": valid.skew(),
            "curtosis": valid.kurt(),
            "atipicos_iqr": int(iqr_outlier_mask(valid).sum()) if valid.size >= 4 else 0,
        })
    return pd.DataFrame(rows)


def frequencies(df: pd.DataFrame, column: str, top: int = 30) -> pd.DataFrame:
    vc = df[column].value_counts(dropna=False).head(top)
    out = vc.rename_axis("valor").reset_index(name="frecuencia")
    out["porcentaje"] = (out["frecuencia"] / len(df) * 100).round(2)
    out["valor"] = out["valor"].astype(str)
    return out


def quality_summary(df: pd.DataFrame, key: tuple[str, ...] = DEFAULT_KEY) -> dict:
    """Resumen de calidad: nulos, duplicados, inconsistencias, rangos, tipos e información insuficiente."""
    report = validate(df, key=key)
    by_code: dict[str, list] = {}
    for i in report.issues:
        by_code.setdefault(i.code, []).append({"columna": i.column, "conteo": i.count, "mensaje": i.message})
    key_cols = [k for k in key if k in df.columns]
    return {
        "filas": len(df),
        "columnas": df.shape[1],
        "celdas_nulas": int(df.isna().sum().sum()),
        "pct_celdas_nulas": round(float(df.isna().mean().mean() * 100), 2) if df.size else 0.0,
        "filas_duplicadas": int(df.duplicated().sum()),
        "llaves_duplicadas": int(df.duplicated(subset=key_cols).sum()) if key_cols else None,
        "es_valido": report.is_valid,
        "problemas": by_code,
    }


def correlation_matrix(df: pd.DataFrame, method: str = "spearman", columns: list[str] | None = None) -> pd.DataFrame:
    cols = columns or numeric_columns(df)
    return df[cols].apply(pd.to_numeric, errors="coerce").corr(method=method)


def target_correlations(df: pd.DataFrame, target: str, method: str = "spearman") -> pd.DataFrame:
    cols = [c for c in numeric_columns(df) if c != target]
    corr = df[cols].corrwith(df[target], method=method)
    return (pd.DataFrame({"variable": corr.index, "correlacion": corr.values})
            .assign(abs_corr=lambda d: d.correlacion.abs())
            .sort_values("abs_corr", ascending=False)
            .drop(columns="abs_corr")
            .reset_index(drop=True))


def group_summary(df: pd.DataFrame, group: str, value: str) -> pd.DataFrame:
    g = df.groupby(group)[value]
    return g.agg(n="count", media="mean", mediana="median", desv="std", minimo="min", maximo="max").reset_index()
