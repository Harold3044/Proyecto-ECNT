"""Selección e interpretación de variables.

IMPORTANTE: todas las funciones de este módulo deben recibir SOLO los datos de entrenamiento.
El flujo de :mod:`ecnt_core.experiment` lo garantiza particionando antes de rankear.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import f_regression, mutual_info_regression
from sklearn.impute import SimpleImputer
from statsmodels.stats.outliers_influence import variance_inflation_factor


def _clean_xy(X: pd.DataFrame, y: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
    X = X.apply(pd.to_numeric, errors="coerce")
    mask = y.notna()
    X, y = X[mask], y[mask]
    Xi = pd.DataFrame(SimpleImputer(strategy="median").fit_transform(X), columns=X.columns, index=X.index)
    return Xi, y.astype(float)


def rank_features(X_train: pd.DataFrame, y_train: pd.Series, seed: int = 42) -> pd.DataFrame:
    """Ranking combinado de relevancia con 4 criterios (todos calculados en entrenamiento):

    |Spearman|, F de regresión univariada (p‑valor), información mutua e importancia de
    Random Forest. ``rank_promedio`` resume los cuatro (1 = más relevante).
    """
    X, y = _clean_xy(X_train, y_train)
    rho = [stats.spearmanr(X[c], y, nan_policy="omit").statistic for c in X.columns]
    f, p = f_regression(X, y)
    mi = mutual_info_regression(X, y, random_state=seed)
    rf = RandomForestRegressor(n_estimators=300, max_depth=6, min_samples_leaf=3, random_state=seed, n_jobs=-1)
    rf.fit(X, y)
    out = pd.DataFrame({
        "variable": X.columns,
        "spearman": np.round(rho, 4),
        "f_estadistico": np.round(f, 3),
        "p_valor": p,
        "info_mutua": np.round(mi, 4),
        "importancia_rf": np.round(rf.feature_importances_, 4),
    })
    ranks = pd.DataFrame({
        "r1": out["spearman"].abs().rank(ascending=False),
        "r2": out["f_estadistico"].rank(ascending=False),
        "r3": out["info_mutua"].rank(ascending=False),
        "r4": out["importancia_rf"].rank(ascending=False),
    })
    out["rank_promedio"] = ranks.mean(axis=1).round(2)
    return out.sort_values("rank_promedio").reset_index(drop=True)


def vif(X_train: pd.DataFrame) -> pd.DataFrame:
    """Factor de inflación de la varianza (multicolinealidad). VIF > 10 indica colinealidad alta."""
    X, _ = _clean_xy(X_train, pd.Series(0.0, index=X_train.index))
    X = X.loc[:, X.std() > 0]
    Xc = sm.add_constant(X, has_constant="add")
    vals = [variance_inflation_factor(Xc.values, i + 1) for i in range(X.shape[1])]
    return (pd.DataFrame({"variable": X.columns, "vif": np.round(vals, 2)})
            .sort_values("vif", ascending=False).reset_index(drop=True))


def ols_table(X_train: pd.DataFrame, y_train: pd.Series) -> tuple[pd.DataFrame, dict]:
    """Regresión múltiple con statsmodels sobre variables estandarizadas.

    Devuelve coeficientes estandarizados, error estándar, p‑valor e IC 95 %, más R² ajustado.
    Útil para el análisis estadístico; los coeficientes son asociaciones, no efectos causales.
    """
    X, y = _clean_xy(X_train, y_train)
    X = X.loc[:, X.std() > 0]
    Xs = (X - X.mean()) / X.std()
    res = sm.OLS(y, sm.add_constant(Xs)).fit()
    ci = res.conf_int()
    table = pd.DataFrame({
        "variable": res.params.index,
        "coef_estandarizado": res.params.values.round(3),
        "error_estandar": res.bse.values.round(3),
        "p_valor": res.pvalues.values,
        "ic95_inf": ci[0].values.round(3),
        "ic95_sup": ci[1].values.round(3),
    })
    table = table[table.variable != "const"].sort_values("p_valor").reset_index(drop=True)
    summary = {"r2": float(res.rsquared), "r2_ajustado": float(res.rsquared_adj), "n": int(res.nobs),
               "f_pvalor": float(res.f_pvalue)}
    return table, summary


def select_top(ranking: pd.DataFrame, k: int | None = None, max_p: float | None = None) -> list[str]:
    """Selecciona variables del ranking: las ``k`` primeras y/o con p‑valor univariado ≤ ``max_p``."""
    r = ranking
    if max_p is not None:
        r = r[r["p_valor"] <= max_p]
    if k is not None:
        r = r.head(k)
    return r["variable"].tolist()
