"""Limpieza y transformación declarativa con linaje.

Cada operación recibe un DataFrame y devuelve uno NUEVO más un detalle de lo que hizo.
:func:`apply_steps` ejecuta una lista de pasos ``{"op": nombre, **parámetros}`` y devuelve
el resultado y el registro, que la API guarda como linaje de la versión.

Nota metodológica: la imputación, el escalado y la codificación para MODELAR se ajustan
dentro del pipeline de scikit-learn con datos de entrenamiento (ver :mod:`ecnt_core.models`).
Las operaciones de este módulo con estadísticos globales (imputar, estandarizar, recortar
atípicos) se marcan con ``usa_estadisticos_globales=True`` en el registro para advertirlo.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from ecnt_core.io import normalize_codes

OpFunc = Callable[..., tuple[pd.DataFrame, dict]]
OPERATIONS: dict[str, dict[str, Any]] = {}


class CleaningError(ValueError):
    pass


def operation(name: str, description: str, global_stats: bool = False):
    def deco(fn: OpFunc) -> OpFunc:
        OPERATIONS[name] = {"fn": fn, "descripcion": description, "usa_estadisticos_globales": global_stats}
        return fn
    return deco


def _require(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise CleaningError(f"Columnas inexistentes: {missing}")


@operation("drop_duplicates", "Elimina filas duplicadas (completas o por llave)")
def drop_duplicates(df, subset: list[str] | None = None, keep: str = "first"):
    if subset:
        _require(df, subset)
    out = df.drop_duplicates(subset=subset or None, keep=keep)
    return out, {"filas_eliminadas": len(df) - len(out)}


@operation("drop_columns", "Elimina columnas")
def drop_columns(df, columns: list[str]):
    _require(df, columns)
    return df.drop(columns=columns), {"columnas_eliminadas": columns}


@operation("rename_columns", "Renombra columnas")
def rename_columns(df, mapping: dict[str, str]):
    _require(df, list(mapping))
    return df.rename(columns=mapping), {"renombradas": mapping}


@operation("cast_numeric", "Convierte columnas a numéricas (valores no convertibles quedan nulos)")
def cast_numeric(df, columns: list[str], decimal: str = "."):
    _require(df, columns)
    out = df.copy()
    nuevos_nulos = {}
    for c in columns:
        s = out[c]
        if decimal == "," and not pd.api.types.is_numeric_dtype(s):
            s = s.astype("string").str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        conv = pd.to_numeric(s, errors="coerce")
        nuevos_nulos[c] = int(conv.isna().sum() - df[c].isna().sum())
        out[c] = conv
    return out, {"nuevos_nulos": nuevos_nulos}


@operation("normalize_codes", "Normaliza códigos DIVIPOLA a texto con ceros a la izquierda")
def normalize_codes_op(df):
    return normalize_codes(df), {}


@operation("impute", "Imputa valores faltantes (mediana, media, moda o constante)", global_stats=True)
def impute(df, columns: list[str], strategy: str = "median", value: Any = None):
    _require(df, columns)
    out = df.copy()
    filled = {}
    for c in columns:
        n = int(out[c].isna().sum())
        if strategy == "median":
            v = pd.to_numeric(out[c], errors="coerce").median()
        elif strategy == "mean":
            v = pd.to_numeric(out[c], errors="coerce").mean()
        elif strategy == "mode":
            m = out[c].mode()
            v = m.iloc[0] if len(m) else None
        elif strategy == "constant":
            v = value
        else:
            raise CleaningError(f"Estrategia de imputación desconocida: {strategy}")
        out[c] = out[c].fillna(v)
        filled[c] = {"imputados": n, "valor": None if v is None else (float(v) if isinstance(v, int | float |
                                                                                             np.number) else v)}
    return out, {"imputacion": filled}


@operation("drop_missing", "Elimina filas con nulos en las columnas indicadas (o en cualquiera)")
def drop_missing(df, columns: list[str] | None = None):
    if columns:
        _require(df, columns)
    out = df.dropna(subset=columns or None)
    return out, {"filas_eliminadas": len(df) - len(out)}


@operation("clip_outliers_iqr", "Recorta (winsoriza) atípicos con el criterio IQR", global_stats=True)
def clip_outliers_iqr(df, columns: list[str], k: float = 1.5):
    _require(df, columns)
    out = df.copy()
    det = {}
    for c in columns:
        s = pd.to_numeric(out[c], errors="coerce")
        q1, q3 = s.quantile([0.25, 0.75])
        lo, hi = q1 - k * (q3 - q1), q3 + k * (q3 - q1)
        det[c] = {"recortados": int(((s < lo) | (s > hi)).sum()), "limites": [float(lo), float(hi)]}
        out[c] = s.clip(lo, hi)
    return out, det


@operation("clip_range", "Recorta valores a un rango válido [min, max]")
def clip_range(df, column: str, min: float | None = None, max: float | None = None):  # noqa: A002
    _require(df, [column])
    s = pd.to_numeric(df[column], errors="coerce")
    mask = pd.Series(False, index=s.index)
    if min is not None:
        mask |= s < min
    if max is not None:
        mask |= s > max
    out = df.copy()
    out[column] = s.clip(min, max)
    return out, {"recortados": int(mask.sum())}


@operation("set_null_out_of_range", "Marca como nulos los valores fuera de rango (para tratarlos después)")
def set_null_out_of_range(df, column: str, min: float | None = None, max: float | None = None):  # noqa: A002
    _require(df, [column])
    s = pd.to_numeric(df[column], errors="coerce")
    mask = pd.Series(False, index=s.index)
    if min is not None:
        mask |= s < min
    if max is not None:
        mask |= s > max
    out = df.copy()
    out[column] = s.mask(mask)
    return out, {"anulados": int(mask.sum())}


@operation("log1p", "Crea columnas transformadas con log(1+x) para variables sesgadas")
def log1p(df, columns: list[str], suffix: str = "_log"):
    _require(df, columns)
    out = df.copy()
    for c in columns:
        s = pd.to_numeric(out[c], errors="coerce")
        if (s < 0).any():
            raise CleaningError(f"log1p no admite valores negativos en '{c}'")
        out[f"{c}{suffix}"] = np.log1p(s)
    return out, {"nuevas_columnas": [f"{c}{suffix}" for c in columns]}


@operation("one_hot", "Codifica variables categóricas en indicadores 0/1")
def one_hot(df, columns: list[str], drop_first: bool = False):
    _require(df, columns)
    out = pd.get_dummies(df, columns=columns, drop_first=drop_first, dtype=int)
    return out, {"nuevas_columnas": [c for c in out.columns if c not in df.columns]}


@operation("standardize", "Estandariza (media 0, desviación 1). Solo para exploración", global_stats=True)
def standardize(df, columns: list[str]):
    _require(df, columns)
    out = df.copy()
    for c in columns:
        s = pd.to_numeric(out[c], errors="coerce")
        sd = s.std()
        out[c] = (s - s.mean()) / sd if sd else 0.0
    return out, {"advertencia": "Para modelar, el escalado se ajusta dentro del pipeline solo con entrenamiento."}


@operation("filter_rows", "Filtra filas según una condición sobre una columna")
def filter_rows(df, column: str, operator: str, value: Any):
    _require(df, [column])
    s = df[column]
    ops = {
        "==": s == value, "!=": s != value,
        ">": pd.to_numeric(s, errors="coerce") > value, ">=": pd.to_numeric(s, errors="coerce") >= value,
        "<": pd.to_numeric(s, errors="coerce") < value, "<=": pd.to_numeric(s, errors="coerce") <= value,
        "in": s.isin(value if isinstance(value, list) else [value]),
        "notnull": s.notna(),
    }
    if operator not in ops:
        raise CleaningError(f"Operador no soportado: {operator}")
    out = df[ops[operator].fillna(False)]
    return out, {"filas_eliminadas": len(df) - len(out)}


def apply_steps(df: pd.DataFrame, steps: list[dict]) -> tuple[pd.DataFrame, list[dict]]:
    """Aplica pasos en orden sin modificar ``df``. Devuelve (nuevo_df, linaje)."""
    out = df.copy()
    log = []
    for i, step in enumerate(steps, start=1):
        params = {k: v for k, v in step.items() if k != "op"}
        name = step.get("op")
        if name not in OPERATIONS:
            raise CleaningError(f"Paso {i}: operación desconocida '{name}'")
        before = out.shape
        try:
            out, detail = OPERATIONS[name]["fn"](out, **params)
        except TypeError as exc:
            raise CleaningError(f"Paso {i} ({name}): parámetros inválidos — {exc}") from exc
        log.append({
            "paso": i, "op": name, "parametros": params,
            "filas_antes": before[0], "filas_despues": out.shape[0],
            "columnas_antes": before[1], "columnas_despues": out.shape[1],
            "usa_estadisticos_globales": OPERATIONS[name]["usa_estadisticos_globales"],
            "detalle": detail,
        })
    return out.reset_index(drop=True), log


def list_operations() -> list[dict]:
    return [{"op": k, "descripcion": v["descripcion"], "usa_estadisticos_globales": v["usa_estadisticos_globales"]}
            for k, v in OPERATIONS.items()]
