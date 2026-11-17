"""Partición reproducible de datos en entrenamiento y prueba.

La partición se define por **identificadores de territorio**, no por posiciones de fila, para
que se pueda guardar, auditar y reproducir. El conjunto de prueba nunca participa en la
selección de variables, el ajuste de transformaciones ni la búsqueda de hiperparámetros.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, train_test_split

ALLOWED_TEST_SIZES = {"70/30": 0.30, "75/25": 0.25, "80/20": 0.20, "90/10": 0.10}
STRATEGIES = ("aleatoria", "agrupada", "geografica", "temporal")


class SplitError(ValueError):
    pass


@dataclass
class SplitResult:
    strategy: str
    test_size: float
    seed: int
    id_col: str
    train_ids: list[str]
    test_ids: list[str]
    group_col: str | None = None
    test_groups: list[str] | None = None
    base_id_col: str | None = None  # solo partición temporal: id del territorio

    def to_dict(self) -> dict:
        return asdict(self)

    def _row_ids(self, df: pd.DataFrame) -> pd.Series:
        if self.id_col == "_row_id":
            return df[self.base_id_col].astype(str) + "|" + df[self.group_col].astype(str)
        return df[self.id_col].astype(str)

    def apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        ids = self._row_ids(df)
        train, test = df[ids.isin(self.train_ids)], df[ids.isin(self.test_ids)]
        if set(self._row_ids(train)) & set(self._row_ids(test)):
            raise SplitError("Fuga: hay observaciones en entrenamiento y prueba a la vez.")
        return train.copy(), test.copy()


def parse_ratio(ratio: str | float) -> float:
    if isinstance(ratio, str):
        if ratio not in ALLOWED_TEST_SIZES:
            raise SplitError(f"Proporción no permitida: {ratio}. Opciones: {list(ALLOWED_TEST_SIZES)}")
        return ALLOWED_TEST_SIZES[ratio]
    if not 0.05 <= ratio <= 0.5:
        raise SplitError("La proporción de prueba debe estar entre 0,05 y 0,5")
    return float(ratio)


def make_split(
    df: pd.DataFrame,
    ratio: str | float = "80/20",
    seed: int = 42,
    strategy: str = "aleatoria",
    id_col: str = "divipola",
    group_col: str | None = None,
    time_col: str | None = None,
    test_groups: list[str] | None = None,
    stratify_target: str | None = None,
) -> SplitResult:
    """Crea una partición.

    - ``aleatoria``: por territorio (cada ``id_col`` va completo a un solo lado). Opcionalmente
      estratificada por quintiles de ``stratify_target`` para equilibrar la distribución del objetivo.
    - ``agrupada``: grupos completos (p. ej. municipio en un panel municipio-año) con ``group_col``.
    - ``geografica``: los grupos de ``test_groups`` (p. ej. un departamento) forman la prueba.
    - ``temporal``: los periodos más recientes de ``time_col`` forman la prueba.
    """
    if strategy not in STRATEGIES:
        raise SplitError(f"Estrategia desconocida: {strategy}")
    if id_col not in df.columns:
        raise SplitError(f"No existe la columna identificadora '{id_col}'")
    test_size = parse_ratio(ratio)
    ids = df[id_col].astype(str)

    if strategy == "aleatoria":
        uniq = df.drop_duplicates(id_col)
        strat = None
        if stratify_target and stratify_target in uniq and uniq[stratify_target].notna().all() and len(uniq) >= 20:
            strat = pd.qcut(uniq[stratify_target], q=5, labels=False, duplicates="drop")
        tr, te = train_test_split(uniq[id_col].astype(str), test_size=test_size, random_state=seed, stratify=strat)
        return SplitResult(strategy, test_size, seed, id_col, sorted(tr), sorted(te))

    if strategy == "agrupada":
        if not group_col or group_col not in df:
            raise SplitError("La partición agrupada requiere 'group_col'")
        gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
        tr_idx, te_idx = next(gss.split(df, groups=df[group_col]))
        return SplitResult(strategy, test_size, seed, id_col, sorted(set(ids.iloc[tr_idx])),
                           sorted(set(ids.iloc[te_idx])), group_col=group_col)

    if strategy == "geografica":
        if not group_col or group_col not in df:
            raise SplitError("La partición geográfica requiere 'group_col' (p. ej. cod_depto)")
        groups = df[group_col].astype(str)
        if not test_groups:
            rng = np.random.default_rng(seed)
            uniq_g = groups.unique()
            n_test = max(1, round(len(uniq_g) * test_size))
            test_groups = sorted(rng.choice(uniq_g, n_test, replace=False).tolist())
        mask = groups.isin([str(g) for g in test_groups])
        if mask.all() or not mask.any():
            raise SplitError("Los grupos de prueba deben dejar datos en ambos conjuntos")
        return SplitResult(strategy, float(mask.mean()), seed, id_col, sorted(set(ids[~mask])), sorted(set(ids[mask])),
                           group_col=group_col, test_groups=[str(g) for g in test_groups])

    # temporal
    if not time_col or time_col not in df:
        raise SplitError("La partición temporal requiere 'time_col'")
    periods = sorted(df[time_col].dropna().unique())
    if len(periods) < 2:
        raise SplitError("La partición temporal requiere al menos dos periodos distintos")
    n_test = max(1, round(len(periods) * test_size))
    test_periods = periods[-n_test:]
    mask = df[time_col].isin(test_periods)
    # En un panel, un territorio aparece en ambos periodos: la llave de la fila es id + periodo
    row_ids = ids + "|" + df[time_col].astype(str)
    return SplitResult(strategy, float(mask.mean()), seed, "_row_id", sorted(row_ids[~mask]),
                       sorted(row_ids[mask]), group_col=time_col, test_groups=[str(p) for p in test_periods],
                       base_id_col=id_col)
