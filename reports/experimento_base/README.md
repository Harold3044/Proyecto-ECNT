# Experimento de referencia — resultados reales (2026-11-17)

**Datos**: 197 municipios del Caribe (DANE, reales). Objetivo: `tasa_mort_ecnt_std` (mortalidad por ECNT cardiometabólicas estandarizada por edad, 2018–2019, por 100.000 hab.). 25 predictores candidatos (NBI 2018 total/cabecera/resto y demografía).
**Diseño**: partición 80/20 aleatoria estratificada (semilla 42; 157 de entrenamiento y 40 de prueba); CV 5 pliegues × 3 repeticiones en entrenamiento; ajuste de hiperparámetros por rejilla dentro de entrenamiento.

## Todas las variables (25)

| Modelo | RMSE CV (media ± DE) | R² CV | RMSE prueba | R² prueba | RMSE entrenamiento |
|---|---|---|---|---|---|
| Línea base (media) | 54,69 ± 5,71 | −0,05 | 57,17 | 0,00 | 54,55 |
| Regresión lineal múltiple | 57,45 ± 10,30 | −0,18 | 53,16 | 0,14 | 44,02 |
| Ridge | 51,01 ± 4,72 | 0,08 | 49,40 | 0,25 | 47,72 |
| **Random Forest (elegido)** | 47,00 ± 6,00 | 0,22 | **46,89** | **0,33** | 25,87 |
| Gradient Boosting | 45,73 ± 6,14 | 0,26 | 47,61 | 0,31 | 36,51 |

Selección: GB tiene el menor RMSE de CV; RF está dentro de 1 error estándar y es más simple → **Random Forest**. Mejora del 14,1 % en RMSE de CV frente a la línea base.

- IC 95 % bootstrap en prueba (RF): RMSE [37,6; 55,4], R² [−0,01; 0,52]. **Muy amplio**: con 40 municipios de prueba la incertidumbre es grande.
- Intervalo de predicción empírico del 90 %: ±82,1 por 100.000; cobertura observada en prueba: 92,5 %.
- La regresión lineal sobreajusta por **multicolinealidad extrema** (VIF de hasta 912 entre NBI total, cabecera y resto).

## Con selección de variables (top 8 del ranking calculado en entrenamiento)

| Modelo | RMSE CV | R² CV | RMSE prueba | R² prueba |
|---|---|---|---|---|
| Línea base | 54,69 | −0,05 | 57,17 | 0,00 |
| Regresión lineal múltiple | 51,39 | 0,06 | 49,26 | 0,26 |
| Ridge | 51,14 | 0,07 | 49,15 | 0,26 |
| Random Forest | 47,14 | 0,22 | 47,66 | 0,30 |
| Gradient Boosting | 47,88 | 0,19 | 48,96 | 0,27 |

La selección corrige la regresión lineal (ahora supera a la línea base). Variables elegidas: `pct_poblacion_resto`, `comp_vivienda_cab`, `comp_vivienda_total`, `miseria_total`, `poblacion_2018`, `comp_vivienda_resto`, `nbi_total`, `comp_hacinamiento_total`.

## Validación externa (917 municipios de otras regiones, nunca vistos)

| Modelo | MAE | RMSE | R² |
|---|---|---|---|
| Línea base | 43,98 | 57,22 | −0,01 |
| Lineal | 58,86 | 76,08 | −0,78 |
| Ridge | 42,66 | 55,28 | 0,06 |
| Random Forest | 42,22 | 54,70 | 0,08 |
| Gradient Boosting | 43,38 | 55,89 | 0,04 |

El modelo **apenas transfiere** a otras regiones: la relación entre determinantes y mortalidad registrada es específica del contexto.

## Interpretación honesta
- Los determinantes sociales disponibles explican una parte **modesta** (≈ 20–30 %) de la variación territorial de la mortalidad registrada por ECNT en el Caribe.
- La variable más relevante es `pct_poblacion_resto` (ruralidad), con asociación **negativa**: es coherente con el subregistro (hallazgo H‑1), no necesariamente con menor riesgo.
- Hay sesgos por departamento en la prueba (Cesar subestimado en −41,8; Sucre sobreestimado en +38,4), con pocos municipios por grupo.
- El modelo sirve para **priorización exploratoria y detección de territorios atípicos** (residuos grandes), no para predicción precisa.
