# Estrategia de datos y variable objetivo (Bloque A — Fase 2)

> Estado: **PROPUESTA para aprobación** (2026-11-17).

## 1. Resultado de la investigación de fuentes

| Fuente | ¿Accesible ya? | ¿Identifica rural disperso? | Nivel | Decisión |
|---|---|---|---|---|
| NBI CNPV 2018 (DANE) | Sí (local) | No (centros poblados + rural disperso) | Municipio × área, 2018 | **Predictores** |
| Proyecciones de población (DANE) | Sí (descargado) | No (ídem) | Municipio × área × edad × año | **Denominadores y predictores demográficos** |
| EEVV defunciones, Cuadro 5 (DANE) | Sí (descargado, 2018–2021) | No en el cuadro; sí en microdatos | Municipio de residencia × causa × edad × año | **Variable objetivo** |
| Microdatos censales | Solo Cesar (local) | Sí (`UA_CLASE`) | Persona/vivienda | No se usa en el modelo (cobertura 25/197 municipios) |
| RIPS / cubos SISPRO | No (requiere usuario institucional) | No (zona U/R) | Municipio | Trabajo futuro |
| ENSIN | No descargada | No | Región/departamento | No sirve como objetivo municipal (C‑7) |

## 2. Variable objetivo propuesta

**`tasa_mort_ecnt_std`**: tasa de mortalidad por ECNT cardiometabólicas **estandarizada por edad**, por 100.000 habitantes, según municipio de residencia, agregando **2018–2019**.

- Causas (lista 6/67 OPS): 302 hipertensivas, 303 isquémicas del corazón, 304 cardiopulmonar y otras del corazón, 306 insuficiencia cardíaca, 307 cerebrovasculares, 309 demás circulatorias, 601 diabetes mellitus.
- Estandarización directa con la población de Colombia 2018 como estándar. Las defunciones de edad desconocida se redistribuyen proporcionalmente.
- Se agregan dos años para reducir la inestabilidad de los municipios pequeños. Se excluyen 2020–2021 por el efecto de la pandemia; quedan en el panel para el seguimiento temporal en el ambiente EPS.

### Por qué no es la fórmula original
La fórmula *personas únicas con ECNT en rural disperso / población rural dispersa × 1.000* requiere RIPS identificados y una desagregación por rural disperso que **ninguna fuente accesible ofrece** (C‑2). La mortalidad es un indicador **registrado, oficial, poblacional y verificable**. Distinciones:

| Concepto | ¿Es lo que medimos? |
|---|---|
| Prevalencia registrada | No |
| Incidencia | No |
| Tasa de personas atendidas | No |
| Riesgo futuro individual | No |
| **Mortalidad registrada por ECNT, ajustada por edad, territorial** | **Sí** |

El componente "población dispersa" entra por los **predictores**: NBI del área resto (`*_resto`), brecha cabecera‑resto y `pct_poblacion_resto`.

## 3. Hallazgos de la validación inicial

**H‑1. Relación inversa con la ruralidad (sesgo de registro probable).** Correlación de Spearman con la variable objetivo: `pct_poblacion_resto` −0,37, `nbi_total` −0,24, `comp_servicios_total` −0,26, `poblacion_2018` +0,33. Las tasas más bajas son Uribia (18,5) y Manaure (25,0), en La Guajira: territorios wayuu muy dispersos, donde es conocido el subregistro de defunciones y de causa. Interpretación: los municipios más rurales y pobres **registran** menos mortalidad por ECNT. Esto refleja una combinación de (a) subregistro y menor certificación médica de la causa, (b) transición epidemiológica (urbanización, estilos de vida) y (c) causas competitivas. El modelo predecirá **mortalidad registrada**. Su uso en las alertas debe incluir la bandera "posible subregistro" en lugar de etiquetar a los territorios rurales como de bajo riesgo.

**H‑2. Conteos pequeños.** 18 de 197 municipios tienen menos de 20 defunciones por ECNT en dos años: tasas inestables. Se propone ponderar por población en el entrenamiento o evaluar con suavizado (Bloque B).

**H‑3. Calidad.** 197 municipios, sin duplicados, sin nulos en predictores ni en el objetivo. Totales verificados contra cifras oficiales.

## 4. Datos sintéticos
No se necesitan para el modelo principal. Solo se generarán pequeños archivos **`SINTETICO_*`** para las pruebas automáticas y para demostrar la carga de "datos nuevos", marcados con `es_sintetico = True`.

## 5. Limitaciones que deben declararse en la entrega
1. El objetivo es mortalidad, no prevalencia ni riesgo individual.
2. No se separa el rural disperso puro; se usa "resto" (centros poblados + rural disperso).
3. Los predictores son de 2018 (único corte censal): el diseño es transversal con el objetivo 2018–2019, no una predicción de series de tiempo.
4. n = 197 municipios: las métricas tendrán intervalos amplios.
5. Asociación ≠ causalidad; riesgo de falacia ecológica.
