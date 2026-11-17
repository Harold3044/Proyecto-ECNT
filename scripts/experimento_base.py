"""Experimento de referencia con DATOS REALES (Caribe) y validación externa (otras regiones).

Uso:  python scripts/experimento_base.py [--ratio 80/20] [--seed 42]
Salidas en reports/experimento_base/ (métricas, tablas y gráficos HTML) y el modelo elegido
en data/storage/modelos/referencia/ (no versionado).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ecnt_core import eda, evaluation, features, plots, registry
from ecnt_core.config import DATA, PROCESSED, ROOT
from ecnt_core.experiment import ExperimentConfig, compare_algorithms, default_features
from ecnt_core.io import read_path

OUT = ROOT / "reports" / "experimento_base"


def save_fig(fig, name: str) -> None:
    fig.write_html(OUT / f"{name}.html", include_plotlyjs="cdn", full_html=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ratio", default="80/20")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    df = read_path(PROCESSED / "caribe_modelado.csv")
    ext = read_path(PROCESSED / "externo_otras_regiones_modelado.csv")
    target = "tasa_mort_ecnt_std"
    feats = default_features(df, target)
    print(f"Datos: {len(df)} municipios del Caribe, {len(feats)} predictores candidatos.")
    print("Calidad:", {k: v for k, v in eda.quality_summary(df).items() if k != "problemas"})

    # Diagnóstico de colinealidad y análisis estadístico (todo el Caribe, solo descriptivo)
    features.vif(df[feats]).to_csv(OUT / "vif.csv", index=False)

    base = ExperimentConfig(target=target, features=feats, ratio=args.ratio, seed=args.seed, cv_splits=5,
                            cv_repeats=3, tune=True)
    results, choice, table = compare_algorithms(df, base)
    table.round(3).to_csv(OUT / "comparacion_modelos.csv", index=False)
    print("\n" + table.round(2).to_string(index=False))
    print("\nSelección:", choice["razon"])

    by_algo = {r.summary["algoritmo"]: r for r in results}
    chosen = by_algo[choice["elegido"]] if choice["elegido"] else by_algo["linear"]
    chosen.ranking.round(4).to_csv(OUT / "ranking_variables_entrenamiento.csv", index=False)
    train_ids = chosen.summary["particion"]["train_ids"]
    tr = df[df.divipola.isin(train_ids)]
    ols, ols_s = features.ols_table(tr[feats], tr[target])
    ols.round(4).to_csv(OUT / "ols_entrenamiento.csv", index=False)

    # Validación externa: territorios que NUNCA participaron (otras regiones de Colombia)
    externo = {}
    for algo, r in by_algo.items():
        b = registry.ModelBundle(r.pipeline, {**r.summary, "version": "tmp"})
        p = registry.predict(b, ext)
        externo[algo] = evaluation.metrics(ext[target], p["prediccion"])
    pd.DataFrame(externo).T.round(3).to_csv(OUT / "validacion_externa.csv")
    print(f"\nValidación externa (otras regiones, n={len(ext)}):\n{pd.DataFrame(externo).T.round(2)}")

    # Figuras
    p = chosen.predictions
    save_fig(plots.metric_comparison(table, "rmse"), "comparacion_rmse")
    save_fig(plots.predicted_vs_actual(p.real, p.predicho, p.municipio), "real_vs_predicho_test")
    save_fig(plots.residuals_plot(p.real, p.predicho, p.municipio), "residuos_test")
    save_fig(plots.feature_importance_bar(pd.DataFrame(chosen.summary["importancia_permutacion_test"])),
             "importancia_permutacion")
    save_fig(plots.correlation_heatmap(eda.correlation_matrix(df, columns=[*feats, target])), "correlaciones")

    path = registry.save_bundle(chosen, DATA / "storage" / "modelos" / "referencia", version="referencia-1",
                                extra={"seleccion": choice})
    resumen = {
        "seleccion": choice,
        "modelo_elegido": {k: chosen.summary[k] for k in (
            "algoritmo", "parametros", "rmse_cv_media", "rmse_cv_de", "rmse_test", "mae_test", "r2_test",
            "ic95_test", "semiancho_intervalo_90", "cobertura_intervalo_90_test", "metricas_por_grupo")},
        "ols_entrenamiento": ols_s,
        "validacion_externa": externo,
        "particion": {k: chosen.summary["particion"][k] for k in ("strategy", "test_size", "seed")},
        "n_entrenamiento": chosen.summary["n_entrenamiento"], "n_prueba": chosen.summary["n_prueba"],
        "bundle": str(Path(path).relative_to(ROOT)),
    }
    (OUT / "resumen.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False, default=str), "utf-8")
    print("\nModelo guardado en", path)


if __name__ == "__main__":
    main()
