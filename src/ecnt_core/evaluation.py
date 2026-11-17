"""Métricas, validación cruzada, intervalos bootstrap, análisis por grupo y selección de modelo."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, KFold, RepeatedKFold, cross_val_predict, cross_validate


def metrics(y_true, y_pred) -> dict[str, float]:
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)) if len(y_true) > 1 else float("nan"),
    }


def bootstrap_ci(y_true, y_pred, n_boot: int = 1000, seed: int = 42, alpha: float = 0.05) -> dict[str, list]:
    """Intervalos de confianza (percentil) de MAE, RMSE y R² remuestreando territorios de prueba."""
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    rng = np.random.default_rng(seed)
    n = len(y_true)
    samples = {"mae": [], "rmse": [], "r2": []}
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        m = metrics(y_true[idx], y_pred[idx])
        for k in samples:
            samples[k].append(m[k])
    lo, hi = 100 * alpha / 2, 100 * (1 - alpha / 2)
    return {k: [float(np.nanpercentile(v, lo)), float(np.nanpercentile(v, hi))] for k, v in samples.items()}


def make_cv(n_splits: int = 5, n_repeats: int = 3, seed: int = 42, groups=None):
    if groups is not None:
        return GroupKFold(n_splits=n_splits)
    if n_repeats > 1:
        return RepeatedKFold(n_splits=n_splits, n_repeats=n_repeats, random_state=seed)
    return KFold(n_splits=n_splits, shuffle=True, random_state=seed)


def cross_validate_model(pipeline, X, y, n_splits=5, n_repeats=3, seed=42, groups=None) -> dict:
    """Validación cruzada SOLO sobre entrenamiento. Devuelve media y desviación por métrica."""
    cv = make_cv(n_splits, n_repeats, seed, groups)
    res = cross_validate(clone(pipeline), X, y, cv=cv, groups=groups,
                         scoring={"mae": "neg_mean_absolute_error", "rmse": "neg_root_mean_squared_error",
                                  "r2": "r2"}, n_jobs=1)
    out = {}
    for m in ("mae", "rmse", "r2"):
        v = res[f"test_{m}"] * (-1 if m != "r2" else 1)
        out[f"{m}_cv_media"] = float(np.mean(v))
        out[f"{m}_cv_de"] = float(np.std(v, ddof=1))
        out[f"{m}_cv_pliegues"] = [float(x) for x in v]
    out["n_pliegues"] = len(res["test_r2"])
    return out


def oof_residual_quantile(pipeline, X, y, q: float = 0.9, seed: int = 42, groups=None) -> float:
    """Cuantil del error absoluto fuera de pliegue: semiancho del intervalo de predicción ~(q·100) %.

    Es un intervalo empírico (estilo conformal) calculado solo con entrenamiento.
    """
    cv = GroupKFold(5) if groups is not None else KFold(5, shuffle=True, random_state=seed)
    pred = cross_val_predict(clone(pipeline), X, y, cv=cv, groups=groups)
    return float(np.quantile(np.abs(np.asarray(y, float) - pred), q))


def metrics_by_group(df: pd.DataFrame, group: str, y_col: str = "real", pred_col: str = "predicho",
                     min_n: int = 3) -> pd.DataFrame:
    rows = []
    for g, d in df.groupby(group):
        if len(d) < min_n:
            rows.append({group: g, "n": len(d), "mae": np.nan, "rmse": np.nan, "sesgo_medio": np.nan})
            continue
        m = metrics(d[y_col], d[pred_col])
        rows.append({group: g, "n": len(d), "mae": m["mae"], "rmse": m["rmse"],
                     "sesgo_medio": float((d[y_col] - d[pred_col]).mean())})
    return pd.DataFrame(rows).sort_values("n", ascending=False).reset_index(drop=True)


def select_best_model(results: list[dict], complexity: dict[str, int]) -> dict:
    """Selección metodológica (no solo por R²):

    1. Se descartan los modelos que no superan a la línea base en RMSE de validación cruzada.
    2. Entre los restantes, se identifica el menor RMSE medio de validación cruzada.
    3. **Regla de un error estándar**: se elige el modelo MÁS SIMPLE cuyo RMSE de CV esté dentro
       de 1 error estándar del mejor (prefiere interpretabilidad cuando la diferencia no es clara).
    El conjunto de prueba NO interviene en la selección; solo se informa.
    """
    by_key = {r["algoritmo"]: r for r in results}
    base = by_key.get("baseline")
    candidates = [r for r in results if r["algoritmo"] != "baseline"]
    if base is not None:
        candidates = [r for r in candidates if r["rmse_cv_media"] < base["rmse_cv_media"]]
    if not candidates:
        return {"elegido": None, "razon": "Ningún modelo supera a la línea base en validación cruzada. "
                "No se recomienda publicar un modelo."}
    best = min(candidates, key=lambda r: r["rmse_cv_media"])
    se = best["rmse_cv_de"] / np.sqrt(max(best.get("n_pliegues", 1), 1))
    within = [r for r in candidates if r["rmse_cv_media"] <= best["rmse_cv_media"] + se]
    chosen = min(within, key=lambda r: (complexity.get(r["algoritmo"], 99), r["rmse_cv_media"]))
    razon = (f"Menor RMSE de CV: {best['algoritmo']} ({best['rmse_cv_media']:.2f}). Umbral 1 EE = "
             f"{best['rmse_cv_media'] + se:.2f}. Modelos dentro del umbral: "
             f"{', '.join(r['algoritmo'] for r in within)}. Se elige el más simple: {chosen['algoritmo']}.")
    if base is not None:
        mejora = 100 * (1 - chosen["rmse_cv_media"] / base["rmse_cv_media"])
        razon += f" Mejora frente a la línea base: {mejora:.1f} % en RMSE de CV."
    return {"elegido": chosen["algoritmo"], "razon": razon, "umbral_1ee": float(best["rmse_cv_media"] + se)}
