"""Lectura de las fuentes oficiales del DANE usadas por el proyecto.

- NBI CNPV 2018 por municipio y área.
- Defunciones no fetales, Cuadro 5 (municipio de residencia × causa 6/67 × grupo de edad).
- Proyecciones de población municipal por área, sexo y edad simple (2018-2042).

Todas las funciones devuelven DataFrames "ordenados" (tidy) con la llave ``divipola``
(texto de 5 dígitos). No inventan ni imputan valores: lo que no está en la fuente queda NaN.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from ecnt_core.config import AGE_GROUPS, AGE_LABELS

# ---------------------------------------------------------------------------
# NBI
# ---------------------------------------------------------------------------
NBI_VARS = ["nbi", "miseria", "comp_vivienda", "comp_servicios", "comp_hacinamiento",
            "comp_inasistencia", "comp_dependencia"]
NBI_AREAS = ["total", "cab", "resto"]


def read_nbi(path: str | Path) -> pd.DataFrame:
    """Lee la hoja ``Municipios`` del anexo NBI CNPV 2018.

    Estructura verificada: 4 columnas de identificación seguidas de 3 bloques de 7
    indicadores (Total, Cabeceras, Centros poblados y rural disperso).
    """
    raw = pd.read_excel(path, sheet_name="Municipios", header=None, dtype=str)
    body = raw.iloc[:, :25].copy()
    body.columns = ["cod_depto", "departamento", "cod_mpio", "municipio"] + [
        f"{v}_{a}" for a in NBI_AREAS for v in NBI_VARS
    ]
    # Filas de datos: códigos numéricos de 2 y 3 dígitos
    mask = body["cod_depto"].str.fullmatch(r"\d{2}", na=False) & body["cod_mpio"].str.fullmatch(
        r"\d{3}", na=False
    )
    df = body[mask].copy()
    df["divipola"] = df["cod_depto"] + df["cod_mpio"]
    num_cols = [c for c in df.columns if c.endswith(tuple(f"_{a}" for a in NBI_AREAS))]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["departamento"] = df["departamento"].str.strip()
    df["municipio"] = df["municipio"].str.strip()
    return df[["divipola", "cod_depto", "departamento", "municipio", *num_cols]].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Defunciones (Cuadro 5)
# ---------------------------------------------------------------------------
def _age_column_starts(header_row: pd.Series) -> list[int]:
    """Posiciones de inicio (columna Hombres) de cada grupo de edad en el encabezado."""
    starts = []
    for j, v in header_row.items():
        if isinstance(v, str) and (v.startswith("Menor") or re.match(r"^De \d", v)):
            starts.append(int(j))
    if len(starts) != len(AGE_GROUPS):
        raise ValueError(f"Se esperaban {len(AGE_GROUPS)} grupos de edad, se hallaron {len(starts)}")
    return starts


def _find_header(raw: pd.DataFrame) -> tuple[int, list[int]]:
    for i in range(min(30, len(raw))):
        row = raw.iloc[i]
        if any(isinstance(v, str) and v.startswith("Menor") for v in row):
            starts = _age_column_starts(row)
            unknown = [j for j, v in row.items() if isinstance(v, str) and v.startswith("Edad desc")]
            return i, starts + unknown
    raise ValueError("No se encontró el encabezado de grupos de edad")


def _sum_sexes(raw: pd.DataFrame, start: int) -> pd.Series:
    block = raw.iloc[:, start : start + 3].apply(pd.to_numeric, errors="coerce")
    return block.sum(axis=1, min_count=1)


def _cause_code(s: pd.Series) -> pd.Series:
    """Código de causa de 3 dígitos o ``TOTAL`` (el DANE alterna 'TOTAL'/'Total' según el año)."""
    return s.astype(str).str.strip().str.extract(r"^(\d{3}|TOTAL)", flags=re.IGNORECASE)[0].str.upper()


def _tidy_deaths(rows: pd.DataFrame, raw: pd.DataFrame, starts: list[int], year: int) -> pd.DataFrame:
    out = pd.DataFrame({"divipola": rows["divipola"], "causa": rows["causa"]})
    for label, s in zip([*AGE_LABELS, "desconocida"], starts, strict=True):
        out[f"def_{label}"] = _sum_sexes(raw.loc[rows.index], s).fillna(0).astype(int)
    out["anio"] = year
    return out.reset_index(drop=True)


def read_deaths_cuadro5_2018(path: str | Path, deptos: list[str]) -> pd.DataFrame:
    """Formato 2018: una hoja por departamento; fila de municipio ``'20001 Valledupar'``."""
    frames = []
    for dep in deptos:
        raw = pd.read_excel(path, sheet_name=dep, header=None)
        h, starts = _find_header(raw)
        data = raw.iloc[h + 1 :].copy()
        mun = data[0].astype(str).str.extract(r"^(\d{5})\s")[0].ffill()
        data["divipola"] = mun
        data["causa"] = data[1].astype(str).str.strip()
        data = data[data["divipola"].notna()]
        data["causa"] = _cause_code(data["causa"])
        data = data[data["causa"].notna()]
        frames.append(_tidy_deaths(data, raw, starts, 2018))
    return pd.concat(frames, ignore_index=True)


def read_deaths_cuadro5_unificado(path: str | Path, year: int, deptos: list[str]) -> pd.DataFrame:
    """Formato 2019 en adelante: hoja ``Cuadro5`` única; código DIVIPOLA numérico en la col. 1."""
    raw = pd.read_excel(path, sheet_name="Cuadro5", header=None)
    h, starts = _find_header(raw)
    data = raw.iloc[h + 1 :].copy()
    code = pd.to_numeric(data[1], errors="coerce")
    data["divipola"] = code.dropna().astype(int).astype(str).str.zfill(5).reindex(data.index)
    data = data[data["divipola"].notna() & ~data["divipola"].str.endswith("000")]
    data = data[data["divipola"].str[:2].isin(deptos)]
    # La columna de causa es la primera, a partir de la 3, que contenga "TOTAL" o un código de 3 dígitos
    cause_col = next(j for j in range(2, starts[0]) if data[j].astype(str).str.match(r"^\d{3} ").any())
    data["causa"] = _cause_code(data[cause_col])
    data = data[data["causa"].notna()]
    return _tidy_deaths(data, raw, starts, year)


# ---------------------------------------------------------------------------
# Población
# ---------------------------------------------------------------------------
def read_population(path: str | Path, deptos: list[str], years: list[int]) -> pd.DataFrame:
    """Población por municipio, año, área y grupo de edad del Cuadro 5.

    Devuelve columnas: divipola, anio, area (``total``/``cab``/``resto``), pob_total y
    ``pob_<grupo>`` para cada grupo de :data:`AGE_GROUPS`.
    """
    raw = pd.read_excel(path, sheet_name=2, header=None, engine="calamine", dtype=object)
    hdr = [str(v) for v in raw.iloc[8].tolist()]
    data = raw.iloc[9:].copy()
    data = data[data[0].astype(str).str.zfill(2).isin(deptos)]
    data[4] = pd.to_numeric(data[4], errors="coerce")
    data = data[data[4].isin(years)]
    # columnas "Total N años" (N = 0..100)
    age_cols: dict[int, int] = {}
    for j, name in enumerate(hdr):
        m = re.match(r"^Total (\d+)", name)
        if m:
            age_cols[int(m.group(1))] = j
    if len(age_cols) != 101:
        raise ValueError(f"Se esperaban 101 edades simples, se hallaron {len(age_cols)}")
    area_map = {"Total": "total", "Cabecera Municipal": "cab"}
    out = pd.DataFrame(
        {
            "divipola": data[2].astype(str).str.zfill(5),
            "anio": data[4].astype(int),
            "area": data[5].map(lambda a: area_map.get(str(a).strip(), "resto")),
            "pob_total": pd.to_numeric(data[6], errors="coerce"),
        }
    )
    for label, lo, hi in AGE_GROUPS:
        cols = [age_cols[a] for a in range(lo, hi + 1)]
        out[f"pob_{label}"] = data[cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Tasas
# ---------------------------------------------------------------------------
def age_standardized_rate(
    deaths: pd.DataFrame, pop: pd.DataFrame, std_weights: pd.Series, per: float = 100_000
) -> pd.Series:
    """Tasa estandarizada por edad (método directo).

    ``deaths`` y ``pop`` comparten índice y tienen columnas ``def_<grupo>`` / ``pob_<grupo>``.
    Las defunciones con edad desconocida se redistribuyen proporcionalmente a las conocidas.
    ``std_weights`` suma 1 y está indexado por etiqueta de grupo.
    """
    known = deaths[[f"def_{g}" for g in AGE_LABELS]].sum(axis=1)
    factor = np.where(known > 0, (known + deaths["def_desconocida"]) / known.replace(0, np.nan), 1.0)
    rate = pd.Series(0.0, index=deaths.index)
    for g in AGE_LABELS:
        p = pop[f"pob_{g}"].replace(0, np.nan)
        r = (deaths[f"def_{g}"] * factor) / p
        rate = rate + r.fillna(0) * std_weights[g]
    return rate * per
