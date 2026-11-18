# Decisiones, riesgos y observaciones críticas

> Estado: Fase 0. Las afirmaciones sobre fuentes externas marcadas **[verificar F2]** se basan en conocimiento previo y deben comprobarse en la Fase 2 antes de usarse.

## 1. Observaciones metodológicas críticas

### C‑1. Hoy no existe una variable objetivo real
Todo el modelado previo (Fase 2 de la asignatura) usa etiquetas de salud simuladas. Los R² reportados (0,17 en un caso, 0,84 en otro) **no dicen nada sobre ECNT reales**: miden qué tan bien un algoritmo recupera una señal que el propio equipo generó. Defender esos números como resultado sería un error grave ante un jurado.

### C‑2. La fórmula Y = personas únicas con ECNT en rural disperso / población rural dispersa × 1.000 probablemente no es construible tal cual
| Requisito de la fórmula | Situación esperada | |
|---|---|---|
| Personas **únicas** | Requiere microdatos RIPS con identificador de persona. No son públicos (Ley 1581/2012, habeas data). Los cubos SISPRO sí ofrecen conteos agregados de *personas atendidas* por municipio, con usuario registrado. | [verificar F2] |
| Identificar **rural disperso** en RIPS | El RIPS registra zona de residencia como Urbana/Rural, **no** distingue centro poblado de rural disperso. | [verificar F2] |
| Denominador **rural disperso** por año | El censo 2018 sí lo da por municipio y clase. Las proyecciones DANE municipales se publican por área *cabecera* vs *centros poblados y rural disperso*. Solo 2018 tendría rural disperso puro. | [verificar F2] |
| Misma unidad geográfica | El NBI también agrupa *centros poblados y rural disperso* ("resto"). | Verificado en el archivo local |

**Consecuencia probable**: la unidad realista es **"resto" (centros poblados + rural disperso)** o **"rural" (RIPS zona R)**, no "rural disperso" puro. Cambiar el título del indicador para reflejarlo es más defendible que forzar una equivalencia inexistente.

### C‑3. Sesgo de acceso: "atendidos" ≠ "prevalencia" y el sesgo va en contra de la hipótesis
En zonas rurales dispersas hay menos acceso a servicios, por lo tanto **menos diagnósticos registrados**. Un modelo entrenado con prevalencia *registrada* puede aprender que peores determinantes → **menor** ECNT, que es un artefacto del subregistro y no un hallazgo. Mitigación: llamar a la variable "tasa de personas atendidas con diagnóstico de ECNT", incluir covariables de acceso (aseguramiento, distancia/IPS por habitante si existen) y discutir explícitamente la dirección del sesgo.

### C‑4. Estructura por edad
Las ECNT dependen fuertemente de la edad. Sin estandarizar por edad (o incluir % de población ≥ 60 años como covariable), el modelo aprenderá "municipios más envejecidos = más ECNT" y lo atribuirá a los determinantes sociales. Se propone tasa **estandarizada por edad** (método directo) o, como mínimo, covariables de estructura etaria.

### C‑5. Tamaño muestral pequeño
El Caribe tiene ~197 municipios. Con un único corte (2018) n ≈ 197. Implicaciones:
- Una partición 70/30 deja ~59 municipios de prueba: las métricas tendrán alta varianza. Se mantendrán las particiones configurables que se piden, pero **la selección de modelo se basará en validación cruzada repetida y agrupada**, con el test reservado para una única evaluación final e intervalos de confianza bootstrap.
- Gradient Boosting y Random Forest pueden sobreajustar; la regresión múltiple regularizada (Ridge) debe incluirse como comparador.
- Siempre se reportará la **línea base** (predecir la media de entrenamiento). Un modelo que no la supera no se publica.

### C‑6. La "predicción futura" exige variación temporal de los predictores
Los determinantes reales disponibles son de 2018. Se puede usar un diseño con rezago (X 2018 → Y 2019–2023), pero no se podrá modelar dinámica temporal ni actualizar predicciones con nuevos determinantes sin fuentes anuales (p. ej. IRCA – calidad del agua, INS/SIVICAP; cobertura educativa, MEN; afiliación al SGSSS, MinSalud) [verificar F2]. Repetir el NBI 2018 en cada año (como hizo el dataset simulado) **no** crea información temporal; solo infla artificialmente n e induce fuga si la partición no es por territorio.

### C‑7. ENSIN no sirve como variable objetivo municipal
ENSIN es representativa a nivel regional/departamental, no municipal [verificar F2]. Usarla como predictor municipal daría 8 valores repetidos (uno por departamento): casi colineal con el departamento. Uso propuesto: contexto descriptivo y validación de plausibilidad.

### C‑8. Otras amenazas a la validez
- **Falacia ecológica**: los resultados describen territorios, no personas. Toda la UI debe evitar lenguaje de riesgo individual.
- **Números pequeños**: en municipios con poca población rural, una tasa por 1.000 es inestable → suavizado Empirical Bayes o agregación de varios años.
- **Autocorrelación espacial**: municipios vecinos se parecen; la validación agrupada por departamento o por bloques espaciales es más honesta que la aleatoria.
- **Causalidad**: los modelos son predictivos/asociativos; no estiman efectos causales.

## 2. Alternativas para la variable objetivo (a decidir tras la Fase 2)

| Opción | Definición | Fuente | Ventajas | Limitaciones |
|---|---|---|---|---|
| **A. Tasa de personas atendidas con ECNT (resto/rural)** | Personas atendidas con dx CIE‑10 de ECNT por zona rural / población resto × 1.000, por municipio‑año | Cubos SISPRO (RIPS) + proyecciones DANE | La más cercana a la propuesta original | Acceso con usuario SISPRO; zona U/R ≠ rural disperso; sesgo de acceso (C‑3) |
| **B. Tasa de mortalidad por ECNT en rural disperso** | Defunciones por causas ECNT con área de residencia = rural disperso / población rural dispersa (censo 2018) × 100.000, agregando varios años | Microdatos de Estadísticas Vitales DANE (públicos; incluyen área de residencia) | **Única fuente pública que identifica rural disperso**; registro poblacional, no depende del acceso a consulta | Mide mortalidad, no prevalencia; conteos pequeños → agregar años y suavizar; subregistro rural de defunciones |
| **C. Prevalencia registrada de HTA/DM/ERC** | Prevalencia reportada por aseguradores | Cuenta de Alto Costo (CAC) | Indicador oficial de prevalencia | Desagregación municipal y por zona por verificar; no distingue rural |
| **D. Índice compuesto de vulnerabilidad (no supervisado)** | Índice de determinantes sin variable de salud | NBI + censo | Siempre construible | Deja de ser predicción de ECNT; cambia el tipo de problema |

**Recomendación preliminar**: investigar A y B en paralelo en la Fase 2. Si A es accesible, usarla como objetivo principal; B como objetivo secundario/validación externa (ambas con el mismo pipeline, un experimento por objetivo). Si ninguna es accesible a tiempo, desarrollar la plataforma con **datos sintéticos claramente marcados** y documentarlo como limitación, sin presentar métricas como evidencia epidemiológica.

Definición propuesta de ECNT (CIE‑10), a confirmar: HTA I10–I15, diabetes E10–E14, cardiopatía isquémica I20–I25, enfermedad cerebrovascular I60–I69, EPOC J40–J44, enfermedad renal crónica N18.

## 3. Decisiones propuestas (requieren aprobación)

| ID | Decisión | Recomendación |
|---|---|---|
| AD‑01 | Arquitectura | Monorepo: `ecnt_core` + FastAPI + PostgreSQL + Admin Streamlit + EPS React; Docker Compose |
| AD‑02 | Unidad de análisis | Territorio × periodo, con `clase_area` explícita; nunca mezclar unidades en un mismo dataset de modelado |
| AD‑03 | Validación | CV repetida agrupada por municipio para selección; test reservado + bootstrap; línea base obligatoria |
| AD‑04 | Modelos | Línea base, regresión múltiple (OLS + Ridge), Gradient Boosting, Random Forest |
| AD‑05 | Publicación de modelos | Flujo borrador → evaluado → aprobado → publicado; aprobación humana obligatoria |
| AD‑06 | Predicciones EPS | Precalculadas por lote y versionadas, no en tiempo real |
| AD‑07 | Datos sintéticos | Prefijo `SINTETICO_`, bandera `es_sintetico` en BD y banner visible en ambas apps |
| AD‑08 | Proyecto previo | No reutilizar el dataset de 2.316 registros; reaprovechar ideas/código de `src/ecnt` revisándolo módulo a módulo |

### Decisiones adicionales tras la replanificación (2026-11-17)

| ID | Decisión | Justificación |
|---|---|---|
| AD‑09 | **SQLite** por defecto mediante SQLAlchemy; PostgreSQL opcional con Docker Compose | Sin servicios externos que instalar; se cambia a PostgreSQL con una variable de entorno |
| AD‑10 | **Ambas apps en Streamlit** (Admin en el puerto 8501, EPS en el 8502), separadas y conectadas solo por la API | Un solo lenguaje para un solo desarrollador; React no cabe en 2 días |
| AD‑11 | Python 3.12/3.13 con `venv` único en la raíz y dependencias fijadas | Simplicidad; se mantiene la separación lógica `ecnt_core` / `api` / `apps` |
| AD‑12 | Power BI fuera del alcance; exportación CSV disponible | Duplicaría el dashboard EPS |

### Decisiones del Bloque B
| ID | Decisión | Justificación |
|---|---|---|
| AD‑13 | Selección de modelo: superar la línea base + regla de 1 error estándar sobre el RMSE de CV; la prueba no interviene | Evita elegir por azar de la partición o solo por R² |
| AD‑14 | Validación externa con municipios reales de otras regiones | Datos independientes reales para el Módulo 8, sin sintéticos |
| AD‑15 | Intervalo de predicción empírico del 90 % (cuantil del error fuera de pliegue) | Comunica la incertidumbre a la EPS |
| AD‑16 | Variable objetivo `tasa_mort_ecnt_std` (aprobada por el usuario) | Ver `docs/datos/ESTRATEGIA_DATOS.md` |

### Decisiones del 2026-11-18
| ID | Decisión | Justificación |
|---|---|---|
| AD‑17 | Interfaces Streamlit rediseñadas con el diseño de `ecnt-frontend` (login, barra lateral, tarjetas, colores azul/verde) en lugar de migrar a React | Elegido por el usuario: conserva funciones y pruebas a un día de la entrega |
| AD‑18 | La EPS ve siempre la versión **original** del panel histórico | Una limpieza exploratoria (p. ej. duplicados con llave errónea) no debe alterar lo que ve la EPS |
| AD‑19 | Vista previa obligatoria de la limpieza con advertencia si se elimina más del 20 % de las filas | Se detectó una limpieza que redujo el panel de 788 a 2 filas |
| AD‑20 | Diccionario de variables único en `ecnt_core/schemas.py` (explicación, unidad, fuente, grupo), expuesto en API, apps y Markdown | Las variables no eran comprensibles para el lector |
| AD‑21 | "Pacientes" del diseño original → **Directorio de territorios** | La unidad de análisis es territorial; no se manejan personas |

### Respuestas recibidas
- **D‑01**: entrega el jueves 19‑nov‑2026.
- **D‑06**: repositorio nuevo (lo crea el usuario; el remoto se conecta cuando haya URL).
- **D‑07**: desarrollador único; las tecnologías quedan a criterio del arquitecto (AD‑09 a AD‑12).

## 4. Decisiones pendientes que dependen de ustedes

| ID | Pregunta | Por qué importa |
|---|---|---|
| D‑01 | **¿Fecha de entrega final y calendario de cortes?** | Ver riesgo R‑01. Define si se hace la plataforma completa o un MVP priorizado. |
| D‑02 | ¿Alguno tiene (o puede tramitar) usuario SISPRO para cubos RIPS? | Determina si la opción A es viable. |
| D‑03 | ¿El docente acepta redefinir el objetivo a "resto/rural" o a mortalidad (opción B)? | Cambio de la variable objetivo original. |
| D‑04 | Alcance geográfico: ¿8 departamentos del Caribe (incl. San Andrés) o solo continentales? | San Andrés no tiene población rural dispersa comparable. |
| D‑05 | ¿Qué ECNT incluir? | Afecta códigos CIE‑10 y comparabilidad. |
| D‑06 | ¿Usar el repo existente `LuisSantiago09/riesgo-ecnt` o uno nuevo? | Historial y permisos de los tres integrantes. |
| D‑07 | ¿Luis tiene experiencia en React? Si no: EPS también en Streamlit (más rápido, menos pulido) | Riesgo de la app EPS. |
| D‑08 | ¿Power BI es requisito de la asignatura? | Si lo es, se añade exportación para tablero complementario. |
| D‑09 | ¿Dónde se despliega (local con Docker, servidor universitario, nube gratuita)? | Fase 8. |
| D‑10 | ¿Una o varias EPS con territorios distintos? | Modelo de permisos por territorio. |
| D‑11 | Umbral de supresión de celdas pequeñas y criterios iniciales de alerta | Privacidad y justificación de alertas. |

## 5. Riesgos

| ID | Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|---|
| R‑01 | **Alcance vs. tiempo**: 2 apps + API + ML + alertas para 3 personas al final del semestre | Alta | Alto | MVP priorizado (ver PLAN), contrato de API temprano, trabajo paralelo |
| R‑02 | No obtener datos reales de salud | Alta | Alto | Investigar A y B; plan sintético documentado |
| R‑03 | Sesgo de acceso invierte la relación esperada | Media | Alto | C‑3: renombrar variable, covariables de acceso, discusión |
| R‑04 | n pequeño → métricas inestables | Alta | Medio | CV repetida agrupada, bootstrap, línea base |
| R‑05 | Fuga de información (preprocesamiento fuera de pipeline, filas repetidas por año) | Media | Alto | Pipeline sklearn, partición por territorio, pruebas automáticas de no‑fuga |
| R‑06 | Integración tardía entre frontend y backend | Media | Medio | OpenAPI + mocks desde la primera semana de Fase 5 |
| R‑07 | Exposición de datos sensibles | Baja | Alto | Solo agregados, supresión de celdas, `.gitignore` de `data/`, secretos en `.env` |
| R‑08 | Alertas interpretadas como diagnóstico o estigmatización territorial | Media | Medio | Lenguaje no clínico, justificación de reglas, revisión humana |
| R‑09 | Dependencias de entorno (Python 3.13 global sin librerías, Docker sin verificar) | Media | Bajo | Entorno virtual por paquete con Python 3.12; verificación en Fase 1 |
