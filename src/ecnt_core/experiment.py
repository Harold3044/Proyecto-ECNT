"""Orquestación de experimentos reproducibles.

Flujo (el orden importa para evitar fuga de información):

1. Se eliminan las filas sin variable objetivo (se informa cuántas).
2. Se PARTICIONA (prueba apartada desde el inicio).
3. Ranking y selección de variables SOLO con entrenamiento.
4. Ajuste opcional de hiperparámetros con validación cruzada SOLO en entrenamiento.
5. Validación cruzada del pipeline final en entrenamiento.
6. Ajuste final en entrenamiento y evaluación ÚNICA en prueba.
"""

from __future__ import annotations

import platform
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from sklearn.inspection import permutation_importance
from sklearn.model_selection import GridSearchCV

from ecnt_core import evaluation, features, splitting
from ecnt_core.eda import numeric_columns
from ecnt_core.io import dataframe_sha256
from ecnt_core.models import ALGORITHMS, ModelConfigError, build_pipeline, validate_params
from ecnt_core.schemas import DEFAULT_TARGET, NON_PREDICTORS

TUNING_GRIDS: dict[str, dict[str, list]] = {
    "ridge": {"modelo__alpha": [0.1, 1, 10, 100]},
    "random_forest": {"modelo__max_depth": [3, 6, 10], "modelo__min_samples_leaf": [2, 5, 10]},
    "gradient_boosting": {"modelo__learning_rate": [0.02, 0.05, 0.1], "modelo__max_depth": [1, 2, 3],
                          "modelo__n_estimators": [100, 300]},
}


@dataclass
class ExperimentConfig:
    algorithm: str = "linear"
    target: str = DEFAULT_TARGET
    features: list[str] | None = None  # None = todas las numéricas predictoras disponibles
    categorical_features: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    ratio: str | float = "80/20"
    seed: int = 42
    split_strategy: str = "aleatoria"
    id_col: str = "divipola"
    group_col: str | None = None
    test_groups: list[str] | None = None
    stratify: bool = True
    cv_splits: int = 5
    cv_repeats: int = 3
    selection: str = "none"  # "none" | "ranking_top_k" | "kbest"
    select_k: int | None = None
    select_max_p: float | None = None
    tune: bool = False
    report_group: str | None = "departamento"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExperimentResult:
    config: dict
    summary: dict  # serializable a JSON
    pipeline: Any = None  # sklearn Pipeline ajustado (no serializable a JSON)
    predictions: pd.DataFrame | None = None  # predicciones en prueba
    ranking: pd.DataFrame | None = None


class ExperimentError(ValueError):
    pass


def default_features(df: pd.DataFrame, target: str) -> list[str]:
    return [c for c in numeric_columns(df) if c != target and c not in NON_PREDICTORS]


def _feature_names(pipeline) -> list[str]:
    names = list(pipeline.named_steps["preprocesar"].get_feature_names_out())
    if "seleccionar" in pipeline.named_steps:
        mask = pipeline.named_steps["seleccionar"].get_support()
        names = [n for n, m in zip(names, mask, strict=True) if m]
    return names


def _model_interpretation(pipeline, algorithm: str) -> pd.DataFrame | None:
    model = pipeline.named_steps["modelo"]
    names = _feature_names(pipeline)
    if algorithm in ("linear", "ridge"):
        return pd.DataFrame({"variable": names, "coeficiente_estandarizado": model.coef_}).assign(
            abs_=lambda d: d.coeficiente_estandarizado.abs()).sort_values("abs_", ascending=False).drop(
            columns="abs_").reset_index(drop=True)
    if hasattr(model, "feature_importances_"):
        return pd.DataFrame({"variable": names, "importancia": model.feature_importances_}).sort_values(
            "importancia", ascending=False).reset_index(drop=True)
    return None


def run_experiment(df: pd.DataFrame, cfg: ExperimentConfig) -> ExperimentResult:
    t0 = time.perf_counter()
    if cfg.target not in df.columns:
        raise ExperimentError(f"No existe la variable objetivo '{cfg.target}'")
    if cfg.algorithm not in ALGORITHMS:
        raise ModelConfigError(f"Algoritmo desconocido: {cfg.algorithm}")
    params = validate_params(cfg.algorithm, cfg.params)
    data = df.copy()
    data[cfg.target] = pd.to_numeric(data[cfg.target], errors="coerce")
    n_sin_objetivo = int(data[cfg.target].isna().sum())
    data = data[data[cfg.target].notna()].reset_index(drop=True)

    feats = cfg.features or default_features(data, cfg.target)
    missing = [c for c in [*feats, *cfg.categorical_features] if c not in data.columns]
    if missing:
        raise ExperimentError(f"Variables inexistentes en el dataset: {missing}")
    leak = [c for c in feats if c == cfg.target or c in NON_PREDICTORS]
    if leak:
        raise ExperimentError(f"Estas variables no pueden ser predictoras (fuga/identificador): {leak}")
    if len(data) < 30:
        raise ExperimentError("Se requieren al menos 30 observaciones con variable objetivo")

    # 2. Partición
    split = splitting.make_split(
        data, cfg.ratio, cfg.seed, cfg.split_strategy, cfg.id_col, cfg.group_col,
        test_groups=cfg.test_groups, stratify_target=cfg.target if cfg.stratify else None,
        time_col=cfg.group_col if cfg.split_strategy == "temporal" else None,
    )
    train, test = split.apply(data)

    # 3. Ranking y selección (solo entrenamiento)
    ranking = features.rank_features(train[feats], train[cfg.target], cfg.seed)
    selected = feats
    select_k = None
    if cfg.selection == "ranking_top_k":
        selected = features.select_top(ranking, cfg.select_k, cfg.select_max_p)
        if not selected:
            raise ExperimentError("La selección dejó cero variables; relaje k o el p‑valor")
    elif cfg.selection == "kbest":
        select_k = min(cfg.select_k or len(feats), len(feats))
    elif cfg.selection != "none":
        raise ExperimentError(f"Método de selección desconocido: {cfg.selection}")

    X_tr, y_tr = train[selected + cfg.categorical_features], train[cfg.target]
    X_te, y_te = test[selected + cfg.categorical_features], test[cfg.target]
    groups = train[cfg.group_col] if cfg.split_strategy == "agrupada" and cfg.group_col else None
    pipe = build_pipeline(cfg.algorithm, selected, cfg.categorical_features, params, cfg.seed, select_k)

    # 4. Ajuste de hiperparámetros (opcional, solo entrenamiento)
    tuning = None
    if cfg.tune and cfg.algorithm in TUNING_GRIDS:
        gs = GridSearchCV(pipe, TUNING_GRIDS[cfg.algorithm], scoring="neg_root_mean_squared_error",
                          cv=evaluation.make_cv(cfg.cv_splits, 1, cfg.seed, groups), n_jobs=1)
        gs.fit(X_tr, y_tr, groups=groups)
        best = {k.replace("modelo__", ""): v for k, v in gs.best_params_.items()}
        params = validate_params(cfg.algorithm, {**params, **best})
        pipe = build_pipeline(cfg.algorithm, selected, cfg.categorical_features, params, cfg.seed, select_k)
        tuning = {"mejores": best, "rmse_cv_busqueda": float(-gs.best_score_),
                  "combinaciones": len(gs.cv_results_["params"])}

    # 5. Validación cruzada en entrenamiento
    cv = evaluation.cross_validate_model(pipe, X_tr, y_tr, cfg.cv_splits, cfg.cv_repeats, cfg.seed, groups)
    q90 = evaluation.oof_residual_quantile(pipe, X_tr, y_tr, 0.9, cfg.seed, groups)

    # 6. Ajuste final y evaluación única en prueba
    pipe.fit(X_tr, y_tr)
    pred_tr = pipe.predict(X_tr)
    pred_te = pipe.predict(X_te)
    test_m = evaluation.metrics(y_te, pred_te)
    train_m = evaluation.metrics(y_tr, pred_tr)
    ci = evaluation.bootstrap_ci(y_te, pred_te, seed=cfg.seed)

    id_cols = [c for c in (cfg.id_col, "municipio", "departamento", "cod_depto") if c in test.columns]
    preds = test[id_cols].copy()
    preds["real"] = y_te.values
    preds["predicho"] = pred_te
    preds["residuo"] = preds["real"] - preds["predicho"]
    preds["lim_inf_90"] = pred_te - q90
    preds["lim_sup_90"] = pred_te + q90
    cobertura = float(((preds.real >= preds.lim_inf_90) & (preds.real <= preds.lim_sup_90)).mean())

    perm = permutation_importance(pipe, X_te, y_te, n_repeats=20, random_state=cfg.seed,
                                  scoring="neg_root_mean_squared_error")
    perm_df = pd.DataFrame({"variable": X_te.columns, "importancia": perm.importances_mean,
                            "de": perm.importances_std}).sort_values("importancia", ascending=False)

    by_group = None
    if cfg.report_group and cfg.report_group in preds.columns:
        by_group = evaluation.metrics_by_group(preds, cfg.report_group)

    interp = _model_interpretation(pipe, cfg.algorithm)
    summary = {
        "algoritmo": cfg.algorithm,
        "nombre": ALGORITHMS[cfg.algorithm].name,
        "objetivo": cfg.target,
        "parametros": params,
        "variables": selected,
        "variables_categoricas": cfg.categorical_features,
        "n_total": len(data),
        "n_sin_objetivo_excluidas": n_sin_objetivo,
        "n_entrenamiento": len(train),
        "n_prueba": len(test),
        "particion": split.to_dict(),
        "ajuste_hiperparametros": tuning,
        **cv,
        **{f"{k}_test": v for k, v in test_m.items()},
        **{f"{k}_entrenamiento": v for k, v in train_m.items()},
        "ic95_test": ci,
        "semiancho_intervalo_90": q90,
        "cobertura_intervalo_90_test": cobertura,
        "importancia_permutacion_test": perm_df.round(4).to_dict("records"),
        "interpretacion_modelo": None if interp is None else interp.round(4).to_dict("records"),
        "metricas_por_grupo": None if by_group is None else by_group.round(3).to_dict("records"),
        "huella_datos": dataframe_sha256(df),
        "es_sintetico": bool(df["es_sintetico"].astype(str).str.lower().isin(["true", "1"]).any())
        if "es_sintetico" in df else None,
        "entorno": {"python": platform.python_version(), "sklearn": sklearn.__version__,
                    "pandas": pd.__version__, "numpy": np.__version__},
        "segundos": round(time.perf_counter() - t0, 2),
    }
    return ExperimentResult(cfg.to_dict(), summary, pipe, preds.reset_index(drop=True), ranking)


def compare_algorithms(df: pd.DataFrame, base: ExperimentConfig,
                       algorithms: list[str] | None = None,
                       params: dict[str, dict] | None = None) -> tuple[list[ExperimentResult], dict, pd.DataFrame]:
    """Entrena varios algoritmos con la MISMA partición, variables y semilla; aplica la regla de selección."""
    algorithms = algorithms or ["baseline", "linear", "ridge", "random_forest", "gradient_boosting"]
    params = params or {}
    results = []
    for a in algorithms:
        cfg = ExperimentConfig(**{**base.to_dict(), "algorithm": a, "params": params.get(a, {})})
        results.append(run_experiment(df, cfg))
    rows = [{k: r.summary[k] for k in ("algoritmo", "nombre", "rmse_cv_media", "rmse_cv_de", "mae_cv_media",
                                       "r2_cv_media", "rmse_test", "mae_test", "r2_test", "rmse_entrenamiento",
                                       "n_pliegues")} for r in results]
    table = pd.DataFrame(rows).rename(columns={"nombre": "modelo"})
    choice = evaluation.select_best_model(rows, {k: a.complexity for k, a in ALGORITHMS.items()})
    return results, choice, table
