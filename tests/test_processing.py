"""Pruebas del motor de procesamiento (Fase 3): lectura, validación, EDA y limpieza."""

import numpy as np
import pandas as pd
import pytest

from ecnt_core import cleaning, eda, plots
from ecnt_core.io import DataFileError, read_table
from ecnt_core.validation import validate


# ----------------------------- Lectura --------------------------------------
def test_lee_csv_con_punto_y_coma_latin1_y_conserva_ceros():
    content = "divipola;municipio;nbi_total\n8001;Barranquilla;20,5\n13001;Cartagena;25\n".encode("latin-1")
    df = read_table(content, "datos.csv")
    assert df["divipola"].tolist() == ["08001", "13001"]
    assert list(df.columns) == ["divipola", "municipio", "nbi_total"]


def test_lee_excel(tmp_path, synthetic_df):
    p = tmp_path / "x.xlsx"
    synthetic_df.head(5).to_excel(p, index=False)
    df = read_table(p.read_bytes(), "x.xlsx")
    assert len(df) == 5 and df["divipola"].str.len().eq(5).all()


@pytest.mark.parametrize("name,content", [("a.txt", b"x"), ("a.csv", b""), ("a.xlsx", b"no-es-excel")])
def test_rechaza_archivos_invalidos(name, content):
    with pytest.raises(DataFileError):
        read_table(content, name)


# ---------------------------- Validación ------------------------------------
def test_dataset_sintetico_valido(synthetic_df):
    r = validate(synthetic_df)
    assert r.is_valid
    assert any(i.code == "sintetico" for i in r.issues)


def test_detecta_problemas(synthetic_df):
    df = synthetic_df.copy()
    df.loc[0, "nbi_total"] = 150  # fuera de rango
    df.loc[1, "divipola"] = "123"  # código inválido
    df = pd.concat([df, df.iloc[[5]]])  # fila duplicada
    df["pct_65_mas"] = df["pct_65_mas"].astype(object)
    df.iloc[2, df.columns.get_loc("pct_65_mas")] = "abc"  # tipo incorrecto
    df["constante"] = 1
    codes = {i.code for i in validate(df).issues}
    assert {"fuera_de_rango", "divipola_invalido", "filas_duplicadas", "tipo_incorrecto", "constante"} <= codes
    assert not validate(df).is_valid  # divipola inválido es error


def test_rechaza_columnas_personales(synthetic_df):
    df = synthetic_df.assign(documento_identidad="123")
    r = validate(df)
    assert not r.is_valid and any(i.code == "dato_personal" for i in r.issues)


def test_llave_duplicada_e_informacion_insuficiente(synthetic_df):
    df = synthetic_df.copy()
    df.loc[1, "divipola"] = df.loc[0, "divipola"]
    df["casi_vacia"] = np.nan
    df.loc[0, "casi_vacia"] = 1.0
    codes = {i.code for i in validate(df).issues}
    assert {"llave_duplicada", "informacion_insuficiente"} <= codes


# ------------------------------- EDA ----------------------------------------
def test_estadistica_descriptiva(synthetic_df):
    s = eda.numeric_summary(synthetic_df).set_index("variable")
    assert "nbi_total" in s.index and "divipola" not in s.index
    row = s.loc["nbi_total"]
    assert row["media"] == pytest.approx(synthetic_df.nbi_total.mean())
    assert row["mediana"] == pytest.approx(synthetic_df.nbi_total.median())
    assert row["minimo"] <= row["q1"] <= row["mediana"] <= row["q3"] <= row["maximo"]
    for col in ("moda", "desv_estandar", "asimetria", "atipicos_iqr", "pct_nulos"):
        assert col in s.columns


def test_frecuencias_y_calidad(synthetic_df):
    f = eda.frequencies(synthetic_df, "departamento")
    assert f["frecuencia"].sum() == len(synthetic_df)
    q = eda.quality_summary(synthetic_df)
    assert q["filas"] == len(synthetic_df) and q["filas_duplicadas"] == 0 and q["es_valido"]


def test_correlaciones_con_objetivo(synthetic_df):
    c = eda.target_correlations(synthetic_df, "tasa_mort_ecnt_std")
    assert c.iloc[0]["variable"] == "pct_poblacion_resto"  # señal más fuerte del generador
    assert eda.correlation_matrix(synthetic_df).shape[0] == len(eda.numeric_columns(synthetic_df))


def test_graficos_se_serializan(synthetic_df):
    figs = [
        plots.histogram(synthetic_df, "nbi_total"),
        plots.boxplot_by_group(synthetic_df, "nbi_total", "departamento"),
        plots.correlation_heatmap(eda.correlation_matrix(synthetic_df)),
        plots.frequency_bar(eda.frequencies(synthetic_df, "departamento"), "departamento"),
        plots.missing_bar(synthetic_df.assign(x=np.nan)),
    ]
    assert all(isinstance(f.to_json(), str) for f in figs)


# ----------------------------- Limpieza -------------------------------------
def test_limpieza_no_modifica_original_y_registra_linaje(synthetic_df):
    df = pd.concat([synthetic_df, synthetic_df.head(3)]).reset_index(drop=True)
    df.loc[10, "nbi_total"] = np.nan  # fila no duplicada
    original = df.copy()
    steps = [
        {"op": "drop_duplicates"},
        {"op": "impute", "columns": ["nbi_total"], "strategy": "median"},
        {"op": "clip_outliers_iqr", "columns": ["poblacion_2018"]},
        {"op": "log1p", "columns": ["poblacion_2018"]},
        {"op": "one_hot", "columns": ["departamento"]},
    ]
    out, log = cleaning.apply_steps(df, steps)
    pd.testing.assert_frame_equal(df, original)  # el original no cambia
    assert len(out) == len(synthetic_df)
    assert out["nbi_total"].isna().sum() == 0
    assert "poblacion_2018_log" in out.columns and "departamento_A" in out.columns
    assert [s["op"] for s in log] == [s["op"] for s in steps]
    assert log[0]["filas_antes"] - log[0]["filas_despues"] == 3
    assert log[1]["usa_estadisticos_globales"] is True


def test_cast_numeric_coma_decimal_y_rango():
    df = pd.DataFrame({"divipola": ["08001", "08002"], "x": ["1.234,5", "abc"], "y": [-5, 120]})
    out, log = cleaning.apply_steps(df, [
        {"op": "cast_numeric", "columns": ["x"], "decimal": ","},
        {"op": "clip_range", "column": "y", "min": 0, "max": 100},
    ])
    assert out["x"].iloc[0] == pytest.approx(1234.5) and pd.isna(out["x"].iloc[1])
    assert out["y"].tolist() == [0, 100] and log[1]["detalle"]["recortados"] == 2


def test_operacion_invalida_lanza_error(synthetic_df):
    with pytest.raises(cleaning.CleaningError):
        cleaning.apply_steps(synthetic_df, [{"op": "no_existe"}])
    with pytest.raises(cleaning.CleaningError):
        cleaning.apply_steps(synthetic_df, [{"op": "drop_columns", "columns": ["zzz"]}])
