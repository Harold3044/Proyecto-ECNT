# Motor de procesamiento y Machine Learning (`ecnt_core`)

Librería Python sin dependencias web. La API la usa; las apps nunca la importan directamente.

## Módulos

| Módulo | Responsabilidad | Funciones principales |
|---|---|---|
| `schemas` | Diccionario canónico de variables (tipo, unidad, rango, si es predictora) | `CANONICAL`, `DEFAULT_PREDICTORS`, `NON_PREDICTORS`, `SENSITIVE_PATTERNS` |
| `io` | Lectura de CSV (separador y codificación automáticos) y Excel; normaliza DIVIPOLA | `read_table`, `read_path`, `dataframe_sha256` |
| `validation` | Errores (bloquean) y advertencias (se limpian): columnas obligatorias, datos personales, DIVIPOLA, duplicados, llave, tipos, rangos, nulos, información insuficiente, constantes | `validate` → `ValidationReport` |
| `eda` | Media, mediana, moda, desviación, mín/máx, cuartiles, asimetría, curtosis, atípicos IQR, frecuencias, calidad, correlaciones | `numeric_summary`, `frequencies`, `quality_summary`, `correlation_matrix`, `target_correlations`, `group_summary` |
| `cleaning` | 14 operaciones declarativas con linaje; nunca modifican el original | `apply_steps`, `list_operations` |
| `plots` | Figuras Plotly (EDA y modelado) serializables a JSON | `histogram`, `boxplot_by_group`, `correlation_heatmap`, `predicted_vs_actual`, `residuals_plot`, … |
| `splitting` | Partición 70/30, 75/25, 80/20, 90/10 con semilla: aleatoria (estratificada), agrupada, geográfica, temporal | `make_split` → `SplitResult` (IDs guardables) |
| `features` | Ranking (Spearman, F, información mutua, importancia RF), VIF, tabla OLS | `rank_features`, `vif`, `ols_table`, `select_top` |
| `models` | Catálogo de algoritmos e hiperparámetros validados; pipeline sin fuga | `ALGORITHMS`, `validate_params`, `build_pipeline` |
| `evaluation` | MAE/RMSE/R², IC bootstrap, CV repetida, intervalo empírico 90 %, métricas por grupo, regla de selección | `cross_validate_model`, `bootstrap_ci`, `select_best_model` |
| `experiment` | Orquesta el experimento completo y reproducible | `run_experiment`, `compare_algorithms` |
| `registry` | Exporta (`joblib` + `metadata.json` con SHA‑256), carga verificando integridad y predice sobre datos nuevos | `save_bundle`, `load_bundle`, `predict` |

## Garantías contra la fuga de información
1. La partición ocurre **antes** de cualquier ranking, selección o ajuste.
2. Imputación, escalado, one‑hot y `SelectKBest` viven dentro del `Pipeline` (se reajustan en cada pliegue).
3. La búsqueda de hiperparámetros usa CV **solo** en entrenamiento.
4. La prueba se evalúa una sola vez; la regla de selección **no** la usa.
5. Identificadores, conteos derivados del objetivo y el propio objetivo se rechazan como predictores.
6. Pruebas automáticas: `tests/test_ml.py` (estadísticos del escalador = media de entrenamiento, particiones disjuntas, rechazo de fuga).

## Regla de selección del mejor modelo (no solo R²)
1. Descartar los modelos que no superan a la línea base (predecir la media) en RMSE de CV.
2. Identificar el menor RMSE medio de CV.
3. **Regla de un error estándar**: elegir el modelo más simple dentro de 1 EE del mejor.

## Reproducir el experimento de referencia
```bash
python scripts/construir_dataset_caribe.py   # datos reales desde las fuentes DANE
python scripts/experimento_base.py           # resultados en reports/experimento_base/
```
