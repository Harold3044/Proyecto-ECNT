"""Pruebas del motor de ML (Fase 4) con datos SINTÉTICOS de señal conocida."""

import numpy as np
import pandas as pd
import pytest

from ecnt_core import evaluation, features, plots, registry, splitting
from ecnt_core.experiment import ExperimentConfig, ExperimentError, compare_algorithms, run_experiment
from ecnt_core.models import ModelConfigError, build_pipeline, validate_params

FEATS = ["nbi_total", "comp_servicios_total", "pct_poblacion_resto", "pct_65_mas", "poblacion_2018"]


# ----------------------------- Partición ------------------------------------
@pytest.mark.parametrize("ratio,expected", [("70/30", 0.3), ("75/25", 0.25), ("80/20", 0.2), ("90/10", 0.1)])
def test_proporciones_permitidas(synthetic_df, ratio, expected):
    s = splitting.make_split(synthetic_df, ratio, seed=1)
    assert len(s.test_ids) == pytest.approx(expected * len(synthetic_df), abs=1)
    assert not set(s.train_ids) & set(s.test_ids)


def test_particion_reproducible_con_semilla(synthetic_df):
    a = splitting.make_split(synthetic_df, "80/20", seed=7, stratify_target="tasa_mort_ecnt_std")
    b = splitting.make_split(synthetic_df, "80/20", seed=7, stratify_target="tasa_mort_ecnt_std")
    c = splitting.make_split(synthetic_df, "80/20", seed=8, stratify_target="tasa_mort_ecnt_std")
    assert a.test_ids == b.test_ids and a.test_ids != c.test_ids


def test_particion_geografica_y_agrupada(synthetic_df):
    g = splitting.make_split(synthetic_df, "80/20", strategy="geografica", group_col="cod_depto",
                             test_groups=["20"])
    tr, te = g.apply(synthetic_df)
    assert set(te.cod_depto) == {"20"} and "20" not in set(tr.cod_depto)
    panel = pd.concat([synthetic_df.assign(periodo=p) for p in ("2018", "2019")])
    a = splitting.make_split(panel, "80/20", strategy="agrupada", group_col="divipola")
    tr, te = a.apply(panel)
    assert not set(tr.divipola) & set(te.divipola)


def test_particion_temporal(synthetic_df):
    panel = pd.concat([synthetic_df.assign(periodo=p) for p in ("2018", "2019", "2020", "2021")])
    t = splitting.make_split(panel, "75/25", strategy="temporal", time_col="periodo")
    tr, te = t.apply(panel)
    assert set(te.periodo) == {"2021"} and "2021" not in set(tr.periodo)


def test_proporcion_invalida(synthetic_df):
    with pytest.raises(splitting.SplitError):
        splitting.make_split(synthetic_df, "60/40")


# ------------------------------ Modelos -------------------------------------
def test_hiperparametros_validados():
    assert validate_params("gradient_boosting", {"max_depth": 3})["max_depth"] == 3
    with pytest.raises(ModelConfigError):
        validate_params("gradient_boosting", {"max_depth": 99})
    with pytest.raises(ModelConfigError):
        validate_params("ridge", {"no_existe": 1})


def test_pipeline_no_usa_estadisticos_de_prueba(synthetic_df):
    """El imputador/escalador se ajusta solo con entrenamiento: cambiar la prueba no altera el modelo."""
    s = splitting.make_split(synthetic_df, "80/20", seed=3)
    tr, te = s.apply(synthetic_df)
    p = build_pipeline("linear", FEATS).fit(tr[FEATS], tr.tasa_mort_ecnt_std)
    scaler_mean = p.named_steps["preprocesar"].named_transformers_["num"].named_steps["escalar"].mean_
    assert np.allclose(scaler_mean, tr[FEATS].mean().values)


# ------------------------------ Selección -----------------------------------
def test_ranking_identifica_senal(synthetic_df):
    r = features.rank_features(synthetic_df[FEATS], synthetic_df.tasa_mort_ecnt_std)
    assert r.iloc[0]["variable"] == "pct_poblacion_resto"
    assert r.iloc[-1]["variable"] in {"comp_servicios_total", "poblacion_2018"}  # sin señal
    v = features.vif(synthetic_df[FEATS])
    assert (v.vif >= 1).all()
    t, s = features.ols_table(synthetic_df[FEATS], synthetic_df.tasa_mort_ecnt_std)
    assert s["r2"] > 0.8 and t.iloc[0]["p_valor"] < 0.001


# ----------------------------- Experimento ----------------------------------
def test_experimento_completo_y_reproducible(synthetic_df):
    cfg = ExperimentConfig(algorithm="linear", features=FEATS, seed=11, cv_repeats=1)
    a, b = run_experiment(synthetic_df, cfg), run_experiment(synthetic_df, cfg)
    assert a.summary["rmse_test"] == pytest.approx(b.summary["rmse_test"])
    assert a.summary["r2_test"] > 0.8  # la señal sintética es fuerte
    s = a.summary
    for k in ("mae_cv_media", "rmse_cv_de", "ic95_test", "importancia_permutacion_test", "metricas_por_grupo",
              "semiancho_intervalo_90", "huella_datos", "entorno"):
        assert k in s
    assert s["es_sintetico"] is True
    assert not set(s["particion"]["train_ids"]) & set(s["particion"]["test_ids"])
    assert set(a.predictions.columns) >= {"real", "predicho", "residuo", "lim_inf_90", "lim_sup_90"}


def test_seleccion_por_ranking_y_kbest(synthetic_df):
    r1 = run_experiment(synthetic_df, ExperimentConfig(algorithm="ridge", features=FEATS, selection="ranking_top_k",
                                                       select_k=2, cv_repeats=1))
    assert len(r1.summary["variables"]) == 2
    r2 = run_experiment(synthetic_df, ExperimentConfig(algorithm="linear", features=FEATS, selection="kbest",
                                                       select_k=3, cv_repeats=1))
    assert len(r2.summary["interpretacion_modelo"]) == 3


def test_ajuste_de_hiperparametros(synthetic_df):
    r = run_experiment(synthetic_df, ExperimentConfig(algorithm="ridge", features=FEATS, tune=True, cv_repeats=1))
    assert r.summary["ajuste_hiperparametros"]["combinaciones"] == 4


def test_rechaza_fuga_y_errores(synthetic_df):
    with pytest.raises(ExperimentError):
        run_experiment(synthetic_df, ExperimentConfig(features=["tasa_mort_ecnt_std"]))
    with pytest.raises(ExperimentError):
        run_experiment(synthetic_df, ExperimentConfig(features=["no_existe"]))
    with pytest.raises(ExperimentError):
        run_experiment(synthetic_df.head(20), ExperimentConfig(features=FEATS))


def test_comparacion_y_regla_de_seleccion(synthetic_df):
    base = ExperimentConfig(features=FEATS, cv_repeats=1)
    results, choice, table = compare_algorithms(synthetic_df, base, ["baseline", "linear", "random_forest"])
    assert len(table) == 3
    assert choice["elegido"] == "linear"  # señal lineal: el modelo simple gana o empata
    tests = {r.summary["algoritmo"]: tuple(r.summary["particion"]["test_ids"]) for r in results}
    assert len(set(tests.values())) == 1  # misma partición para todos


def test_regla_un_error_estandar_prefiere_simple():
    rows = [
        {"algoritmo": "baseline", "rmse_cv_media": 50, "rmse_cv_de": 5, "n_pliegues": 5},
        {"algoritmo": "linear", "rmse_cv_media": 30.5, "rmse_cv_de": 4, "n_pliegues": 5},
        {"algoritmo": "gradient_boosting", "rmse_cv_media": 30.0, "rmse_cv_de": 4, "n_pliegues": 5},
    ]
    assert evaluation.select_best_model(rows, {"linear": 1, "gradient_boosting": 4})["elegido"] == "linear"
    rows[1]["rmse_cv_media"] = 60
    assert evaluation.select_best_model(rows, {"linear": 1, "gradient_boosting": 4})["elegido"] == "gradient_boosting"
    rows[2]["rmse_cv_media"] = 70
    assert evaluation.select_best_model(rows, {})["elegido"] is None  # nadie supera la línea base


# ----------------------- Registro y datos nuevos ----------------------------
def test_exportar_cargar_y_predecir_datos_nuevos(synthetic_df, tmp_path):
    r = run_experiment(synthetic_df, ExperimentConfig(algorithm="gradient_boosting", features=FEATS, cv_repeats=1))
    path = registry.save_bundle(r, tmp_path / "v1", version="1")
    b = registry.load_bundle(path)
    nuevos = synthetic_df.sample(10, random_state=0).drop(columns="tasa_mort_ecnt_std")
    nuevos.loc[nuevos.index[0], "nbi_total"] = np.nan  # se imputa con la mediana de ENTRENAMIENTO
    pred = registry.predict(b, nuevos)
    assert len(pred) == 10 and pred["prediccion"].notna().all()
    assert (pred.lim_inf_90 <= pred.prediccion).all() and (pred.prediccion <= pred.lim_sup_90).all()
    assert pred["variables_imputadas"].iloc[0] == 1
    np.testing.assert_allclose(b.pipeline.predict(nuevos[FEATS]), r.pipeline.predict(nuevos[FEATS]))


def test_bundle_alterado_se_detecta(synthetic_df, tmp_path):
    r = run_experiment(synthetic_df, ExperimentConfig(algorithm="linear", features=FEATS, cv_repeats=1))
    path = registry.save_bundle(r, tmp_path / "v1", version="1")
    (path / "model.joblib").write_bytes(b"alterado")
    with pytest.raises(registry.ModelBundleError):
        registry.load_bundle(path)


def test_prediccion_sin_variables_requeridas(synthetic_df, tmp_path):
    r = run_experiment(synthetic_df, ExperimentConfig(algorithm="linear", features=FEATS, cv_repeats=1))
    b = registry.load_bundle(registry.save_bundle(r, tmp_path / "v", "1"))
    with pytest.raises(registry.ModelBundleError):
        registry.predict(b, synthetic_df.drop(columns=["nbi_total"]))


def test_graficos_de_modelado(synthetic_df):
    r = run_experiment(synthetic_df, ExperimentConfig(algorithm="linear", features=FEATS, cv_repeats=1))
    p = r.predictions
    figs = [plots.predicted_vs_actual(p.real, p.predicho), plots.residuals_plot(p.real, p.predicho),
            plots.residual_histogram(p.real, p.predicho),
            plots.feature_importance_bar(pd.DataFrame(r.summary["importancia_permutacion_test"]))]
    assert all(isinstance(f.to_json(), str) for f in figs)
