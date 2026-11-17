"""Pruebas de los lectores DANE y del cálculo de tasas.

Las pruebas marcadas ``datos_reales`` usan los archivos procesados; se omiten si no existen
(los datos no se versionan en Git: se regeneran con scripts/construir_dataset_caribe.py).
"""

import numpy as np
import pandas as pd
import pytest

from ecnt_core.config import AGE_LABELS, CARIBE_DEPTOS, ECNT_CAUSES, PROCESSED
from ecnt_core.sources.dane import _cause_code, age_standardized_rate


def test_cause_code_acepta_mayusculas_y_minusculas():
    s = pd.Series(["TOTAL", "Total", "302 Enfermedades hipertensivas", " 601 Diabetes", "Otro", None])
    assert _cause_code(s).tolist()[:4] == ["TOTAL", "TOTAL", "302", "601"]
    assert _cause_code(s).iloc[4:].isna().all()


def test_definicion_ecnt_excluye_fiebre_reumatica():
    assert "301" not in ECNT_CAUSES
    assert {"302", "303", "307", "601"} <= set(ECNT_CAUSES)


def _frames(deaths_by_group, pop_by_group, unknown=0):
    d = pd.DataFrame([{f"def_{g}": v for g, v in zip(AGE_LABELS, deaths_by_group, strict=True)}])
    d["def_desconocida"] = unknown
    p = pd.DataFrame([{f"pob_{g}": v for g, v in zip(AGE_LABELS, pop_by_group, strict=True)}])
    return d, p


def test_tasa_estandarizada_con_tasa_constante_es_esa_tasa():
    pop = [1000] * len(AGE_LABELS)
    deaths = [1] * len(AGE_LABELS)  # 1 por 1000 en todos los grupos = 100 por 100.000
    w = pd.Series(np.full(len(AGE_LABELS), 1 / len(AGE_LABELS)), index=AGE_LABELS)
    d, p = _frames(deaths, pop)
    assert age_standardized_rate(d, p, w).iloc[0] == pytest.approx(100.0)


def test_edad_desconocida_se_redistribuye_proporcionalmente():
    pop = [1000] * len(AGE_LABELS)
    deaths = [1] * len(AGE_LABELS)
    w = pd.Series(np.full(len(AGE_LABELS), 1 / len(AGE_LABELS)), index=AGE_LABELS)
    d, p = _frames(deaths, pop, unknown=len(AGE_LABELS))  # duplica el total
    assert age_standardized_rate(d, p, w).iloc[0] == pytest.approx(200.0)


def test_poblacion_cero_no_produce_infinito():
    pop = [0] + [1000] * (len(AGE_LABELS) - 1)
    deaths = [0] * len(AGE_LABELS)
    w = pd.Series(np.full(len(AGE_LABELS), 1 / len(AGE_LABELS)), index=AGE_LABELS)
    d, p = _frames(deaths, pop)
    assert np.isfinite(age_standardized_rate(d, p, w).iloc[0])


panel_path = PROCESSED / "caribe_panel_municipio_anio.csv"
datos_reales = pytest.mark.skipif(not panel_path.exists(), reason="datos procesados no generados")


@datos_reales
def test_panel_cuadra_con_totales_oficiales_dane():
    """Totales departamentales publicados por el DANE en el Cuadro 5 (verificados manualmente)."""
    p = pd.read_csv(panel_path, dtype={"divipola": str})
    tot = p.assign(dep=p.divipola.str[:2]).groupby(["dep", "anio"])["def_todas_causas"].sum()
    assert tot[("20", 2018)] == 4910
    assert tot[("20", 2019)] == 4966
    assert tot[("20", 2021)] == 7536
    assert tot[("08", 2020)] == 18494


@datos_reales
def test_panel_es_municipio_anio_unico_y_solo_caribe():
    p = pd.read_csv(panel_path, dtype={"divipola": str})
    assert not p.duplicated(["divipola", "anio"]).any()
    assert set(p.divipola.str[:2]) <= set(CARIBE_DEPTOS)
    assert (~p["es_sintetico"]).all()


@datos_reales
def test_dataset_modelado_completo():
    m = pd.read_csv(PROCESSED / "caribe_modelado.csv", dtype={"divipola": str})
    assert len(m) == m.divipola.nunique() == 197
    assert m["tasa_mort_ecnt_std"].between(0, 2000).all()
    assert m["divipola"].str.fullmatch(r"\d{5}").all()
