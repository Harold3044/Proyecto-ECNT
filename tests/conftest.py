"""Datos de prueba SINTÉTICOS (no reales), generados en memoria con semilla fija."""

import numpy as np
import pandas as pd
import pytest


def make_synthetic(n: int = 120, seed: int = 0) -> pd.DataFrame:
    """Dataset territorial SINTÉTICO con una señal conocida para probar el flujo de ML."""
    rng = np.random.default_rng(seed)
    deps = ["08", "13", "20", "23"]
    cod = rng.choice(deps, n)
    df = pd.DataFrame({
        "divipola": [f"{d}{i:03d}" for i, d in enumerate(cod, start=1)],
        "cod_depto": cod,
        "departamento": pd.Series(cod).map({"08": "A", "13": "B", "20": "C", "23": "D"}),
        "municipio": [f"Municipio sintético {i}" for i in range(n)],
        "periodo": "2018-2019",
        "nbi_total": rng.uniform(10, 80, n),
        "comp_servicios_total": rng.uniform(0, 60, n),
        "pct_poblacion_resto": rng.uniform(5, 90, n),
        "pct_65_mas": rng.uniform(4, 12, n),
        "poblacion_2018": rng.integers(3_000, 400_000, n).astype(float),
    })
    noise = rng.normal(0, 8, n)
    df["tasa_mort_ecnt_std"] = (220 - 1.2 * df.pct_poblacion_resto + 0.6 * df.nbi_total
                                + 6 * df.pct_65_mas + noise).clip(5, None)
    df["es_sintetico"] = True
    return df


@pytest.fixture
def synthetic_df() -> pd.DataFrame:
    return make_synthetic()
