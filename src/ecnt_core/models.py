"""Algoritmos disponibles y construcción de pipelines sin fuga de información.

Todo preprocesamiento (imputación, escalado, codificación, selección de variables) vive
dentro del ``Pipeline``; así se ajusta solo con los datos de entrenamiento de cada pliegue.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Any

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.feature_selection import SelectKBest, f_regression, mutual_info_regression
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass(frozen=True)
class ParamSpec:
    type: str  # "int" | "float" | "choice"
    default: Any
    min: float | None = None
    max: float | None = None
    choices: tuple | None = None
    help: str = ""


@dataclass(frozen=True)
class Algorithm:
    key: str
    name: str
    complexity: int  # para la regla de parsimonia (menor = más simple)
    needs_scaling: bool
    params: dict[str, ParamSpec]
    description: str


ALGORITHMS: dict[str, Algorithm] = {
    a.key: a
    for a in [
        Algorithm("baseline", "Línea base (media)", 0, False, {},
                  "Predice la media del entrenamiento. Todo modelo útil debe superarla."),
        Algorithm("linear", "Regresión lineal múltiple", 1, True, {},
                  "Mínimos cuadrados ordinarios; interpretable mediante coeficientes."),
        Algorithm("ridge", "Regresión múltiple regularizada (Ridge)", 2, True,
                  {"alpha": ParamSpec("float", 1.0, 0.0001, 1000, help="Fuerza de la regularización L2")},
                  "Regresión lineal con penalización L2; más estable con predictores correlacionados."),
        Algorithm("random_forest", "Random Forest", 3, False, {
            "n_estimators": ParamSpec("int", 300, 50, 1000, help="Número de árboles"),
            "max_depth": ParamSpec("int", 6, 1, 30, help="Profundidad máxima"),
            "min_samples_leaf": ParamSpec("int", 3, 1, 50, help="Mínimo de territorios por hoja"),
            "max_features": ParamSpec("choice", "sqrt", choices=("sqrt", "log2", 1.0)),
        }, "Promedio de árboles entrenados con remuestreo; captura no linealidades."),
        Algorithm("gradient_boosting", "Gradient Boosting", 4, False, {
            "n_estimators": ParamSpec("int", 200, 20, 2000, help="Número de etapas"),
            "learning_rate": ParamSpec("float", 0.05, 0.001, 1.0, help="Tasa de aprendizaje"),
            "max_depth": ParamSpec("int", 2, 1, 10, help="Profundidad de cada árbol"),
            "min_samples_leaf": ParamSpec("int", 5, 1, 50),
            "subsample": ParamSpec("float", 0.8, 0.1, 1.0, help="Fracción de datos por etapa"),
        }, "Árboles secuenciales que corrigen el error residual; requiere control del sobreajuste."),
    ]
}


class ModelConfigError(ValueError):
    pass


def validate_params(algorithm: str, params: dict | None) -> dict:
    """Completa con valores por defecto y valida tipos/rangos de los hiperparámetros."""
    if algorithm not in ALGORITHMS:
        raise ModelConfigError(f"Algoritmo desconocido: {algorithm}. Opciones: {list(ALGORITHMS)}")
    spec = ALGORITHMS[algorithm].params
    params = dict(params or {})
    unknown = set(params) - set(spec)
    if unknown:
        raise ModelConfigError(f"Hiperparámetros no válidos para {algorithm}: {sorted(unknown)}")
    out = {}
    for name, p in spec.items():
        v = params.get(name, p.default)
        if p.type == "int":
            v = int(v)
        elif p.type == "float":
            v = float(v)
        elif p.type == "choice":
            if v not in p.choices:
                raise ModelConfigError(f"{name} debe ser uno de {p.choices}")
        if p.min is not None and v < p.min or p.max is not None and v > p.max:
            raise ModelConfigError(f"{name}={v} fuera de rango [{p.min}, {p.max}]")
        out[name] = v
    return out


def _estimator(algorithm: str, params: dict, seed: int):
    if algorithm == "baseline":
        return DummyRegressor(strategy="mean")
    if algorithm == "linear":
        return LinearRegression()
    if algorithm == "ridge":
        return Ridge(**params)
    if algorithm == "random_forest":
        return RandomForestRegressor(random_state=seed, n_jobs=-1, **params)
    if algorithm == "gradient_boosting":
        return GradientBoostingRegressor(random_state=seed, **params)
    raise ModelConfigError(algorithm)


def build_pipeline(
    algorithm: str,
    numeric_features: list[str],
    categorical_features: list[str] | None = None,
    params: dict | None = None,
    seed: int = 42,
    select_k: int | None = None,
    select_score: str = "f_regression",
) -> Pipeline:
    """Pipeline: imputación (+ escalado) / one‑hot → selección opcional → regresor."""
    params = validate_params(algorithm, params)
    categorical_features = categorical_features or []
    num_steps = [("imputar", SimpleImputer(strategy="median"))]
    if ALGORITHMS[algorithm].needs_scaling:
        num_steps.append(("escalar", StandardScaler()))
    transformers = [("num", Pipeline(num_steps), numeric_features)]
    if categorical_features:
        transformers.append(("cat", Pipeline([
            ("imputar", SimpleImputer(strategy="most_frequent")),
            ("codificar", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]), categorical_features))
    steps = [("preprocesar", ColumnTransformer(transformers, remainder="drop", verbose_feature_names_out=False))]
    if select_k:
        if select_score not in ("f_regression", "mutual_info"):
            raise ModelConfigError(f"Criterio de selección desconocido: {select_score}")
        score = (f_regression if select_score == "f_regression"
                 else partial(mutual_info_regression, random_state=seed))  # partial: serializable
        steps.append(("seleccionar", SelectKBest(score, k=select_k)))
    steps.append(("modelo", _estimator(algorithm, params, seed)))
    return Pipeline(steps)


def algorithms_catalog() -> list[dict]:
    return [
        {"key": a.key, "nombre": a.name, "descripcion": a.description, "complejidad": a.complexity,
         "hiperparametros": {k: vars(p) for k, p in a.params.items()}}
        for a in ALGORITHMS.values()
    ]
