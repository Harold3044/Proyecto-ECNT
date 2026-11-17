# Plan de trabajo y backlog inicial

## 0. REPLANIFICACIÓN VIGENTE (2026-11-17)

**Nuevas restricciones**: entrega final **jueves 19‑nov‑2026** (≈ 2 días), **un solo desarrollador** (Harold Solano), repositorio nuevo. Las secciones 1–4 de este documento quedan como plan de referencia del alcance completo; **el plan que rige es este**.

### Cronograma comprimido

| Bloque | Fases | Cuándo | Resultado verificable |
|---|---|---|---|
| A | F1 Preparación + F2 Datos | Mar 17 (noche) | Repo, entorno, pruebas base; dataset real NBI 2018 integrado; decisión de variable objetivo |
| B | F3 Procesamiento + F4 ML | Mié 18 (mañana) | `ecnt_core` con carga, validación, EDA, limpieza, partición, 4 modelos, evaluación y registro, con pytest |
| C | F5 API | Mié 18 (tarde) | FastAPI + SQLite, auth JWT, roles, datasets, experimentos, modelos, predicciones, territorios, alertas, auditoría |
| D | F6 Admin + F7 EPS | Mié 18 (noche) – Jue 19 (mañana) | Dos apps Streamlit independientes conectadas a la API |
| E | F8 Integración | Jue 19 | Pruebas de extremo a extremo y de permisos, Docker Compose, README/manuales, limitaciones |

### Recortes de alcance (justificados por el tiempo)

| Se mantiene (MVP) | Se simplifica | Queda como trabajo futuro |
|---|---|---|
| Carga CSV/Excel + formulario territorial, validación, EDA, limpieza versionada, selección de variables, partición configurable (70/30…90/10 + semilla + agrupada), línea base + regresión múltiple + GB + RF, comparación, pruebas con datos nuevos, registro/aprobación/publicación de modelos, API con roles, dashboard y consulta EPS, alertas con estados e historial | EPS en **Streamlit** (no React); **SQLite** (código compatible con PostgreSQL vía SQLAlchemy); exportación en CSV en lugar de PDF; mapa solo si queda tiempo | React/Astro, PostgreSQL en producción, Power BI, SHAP, validación temporal real, varias EPS con territorios distintos |

Todas las tareas del backlog pasan a ser responsabilidad de Harold Solano.

---

> Plan original de referencia (equipo de 3 personas). Las duraciones son relativas.

## 1. Fases

| Fase | Objetivo | Duración estimada | Entregable verificable |
|---|---|---|---|
| 0 | Inspección y planificación | — | Este conjunto de documentos |
| 1 | Preparación del proyecto | S1 | Estructura, entornos, Git, README, pytest/ruff funcionando, `docker compose up db` operativo |
| 2 | Investigación y validación de datos | S1–S2 (en paralelo con F1) | Fichas de fuentes, decisión de variable objetivo, dataset base real (o sintético marcado) |
| 3 | Motor de procesamiento y análisis (`ecnt_core`) | S2–S3 | Carga, validación, EDA, limpieza y versionado con pruebas |
| 4 | Motor de ML (`ecnt_core`) | S3–S4 | Selección, partición, 4 modelos, evaluación, exportación y versionado |
| 5 | Backend y API | S2–S5 (contrato en S2) | API con auth, roles, carga, experimentos, predicción, territorios, alertas, auditoría |
| 6 | Ambiente administrativo | S3–S5 | App Streamlit conectada a la API |
| 7 | Ambiente EPS | S4–S6 | App React conectada a la API |
| 8 | Integración, pruebas y despliegue | S6–S7 | Docker Compose completo, pruebas E2E, manuales, informe final |

Las fases se **solapan por persona**, pero cada fase se cierra y presenta por separado. El orden de autorización se mantiene.

## 2. Priorización (MVP primero)

**Imprescindible (MVP defendible)**: carga masiva + validación, EDA y calidad, limpieza versionada, partición agrupada, 3 modelos + línea base, comparación, registro y publicación de modelo, API con roles, dashboard y consulta territorial EPS, alertas con estados.

**Deseable**: formulario individual, mapas, comparación de versiones de modelo, exportación de informes PDF, historial completo de alertas con responsables.

**Opcional**: Power BI, separación geográfica/temporal avanzada, SHAP, múltiples EPS con territorios distintos.

## 3. Responsabilidades y trabajo en paralelo

| Integrante | Rol | Trabaja sobre | Depende de |
|---|---|---|---|
| **Diego Nieves** | Ciencia de datos e IA | `packages/ecnt_core`, `scripts/`, `notebooks/`, `docs/datos/` | Solo del esquema canónico (acordado en F1). Usa datos sintéticos/fixtures mientras llegan los reales. |
| **Harold Solano** | Backend e integración | `services/api`, BD, auth, Docker, alertas | Interfaz pública de `ecnt_core` (funciones acordadas, no su implementación). |
| **Luis Vivanco** | Frontend | `apps/admin`, `apps/eps` | Contrato OpenAPI + servidor de mocks (S2). No necesita la API real para avanzar. |

Puntos de sincronización obligatorios (cortos): (1) esquema canónico de observación territorial — F1; (2) contrato OpenAPI — inicio F5; (3) integración — F8.

## 4. Backlog inicial

Prioridad: P1 = MVP, P2 = deseable, P3 = opcional.

| ID | Tarea | Resp. | Fase | P | Depende de |
|---|---|---|---|---|---|
| B‑01 | Crear estructura de carpetas, `.gitignore`, README, `PROJECT_PROGRESS.md` | Harold | 1 | P1 | Aprobación F0 |
| B‑02 | Inicializar Git / conectar repo (según D‑06), ramas `main` + `develop`, convención de commits | Harold | 1 | P1 | D‑06 |
| B‑03 | Entorno Python 3.12 para `ecnt_core` y `api`; pytest + ruff + pre‑commit | Harold | 1 | P1 | B‑01 |
| B‑04 | Esqueleto Vite + React + TS para EPS; esqueleto Streamlit para Admin | Luis | 1 | P1 | B‑01 |
| B‑05 | `docker-compose.yml` con PostgreSQL y `.env.example` | Harold | 1 | P1 | B‑01 |
| B‑06 | Definir esquema canónico de observación territorial (columnas, tipos, rangos) | Diego + Harold | 1 | P1 | — |
| B‑07 | Ficha de fuente: NBI CNPV 2018 (cobertura, variables, clase de área) | Diego | 2 | P1 | — |
| B‑08 | Ficha de fuente: cubos SISPRO/RIPS (acceso, variables, zona, personas únicas) | Diego + Harold | 2 | P1 | D‑02 |
| B‑09 | Ficha de fuente: Estadísticas Vitales DANE (área de residencia, causas CIE‑10) | Diego | 2 | P1 | — |
| B‑10 | Ficha de fuente: proyecciones de población DANE por área y edad | Diego | 2 | P1 | — |
| B‑11 | Ficha de fuente: ENSIN, CAC, IRCA, MEN (utilidad y nivel de desagregación) | Luis | 2 | P2 | — |
| B‑12 | Propuesta formal de variable objetivo con limitaciones | Diego | 2 | P1 | B‑07…B‑10, D‑03 |
| B‑13 | Generador de datos **sintéticos** marcados para pruebas | Diego | 2 | P1 | B‑06 |
| B‑14 | Catálogo DIVIPOLA + GeoJSON municipal del Caribe | Luis | 2 | P2 | — |
| B‑15 | `ecnt_core.io` + `validation` (CSV/Excel, tipos, rangos, llaves, duplicados) | Diego | 3 | P1 | B‑06 |
| B‑16 | `ecnt_core.eda` (descriptivos, frecuencias, calidad, gráficos Plotly) | Diego | 3 | P1 | B‑15 |
| B‑17 | `ecnt_core.cleaning` con linaje de versiones | Diego | 3 | P1 | B‑15 |
| B‑18 | Informe de calidad exportable (HTML/JSON) | Diego | 3 | P2 | B‑16 |
| B‑19 | `ecnt_core.splitting` (70/30…90/10, semilla, agrupada, temporal, geográfica) | Diego | 4 | P1 | B‑17 |
| B‑20 | `ecnt_core.features` (correlación, VIF, importancia por permutación, selección dentro de CV) | Diego | 4 | P1 | B‑19 |
| B‑21 | Modelos: línea base, OLS/Ridge, GB, RF con pipelines | Diego | 4 | P1 | B‑19 |
| B‑22 | Evaluación: MAE/RMSE/R², bootstrap, residuos, desempeño por departamento | Diego | 4 | P1 | B‑21 |
| B‑23 | Registro y exportación de modelos (joblib + hash + metadatos) | Diego + Harold | 4 | P1 | B‑21 |
| B‑24 | Pruebas automáticas de no‑fuga y reproducibilidad | Diego | 4 | P1 | B‑21 |
| B‑25 | Contrato OpenAPI + servidor de mocks | Harold | 5 | P1 | B‑06 |
| B‑26 | Modelos ORM + migraciones Alembic | Harold | 5 | P1 | B‑25 |
| B‑27 | Auth JWT + roles + auditoría | Harold | 5 | P1 | B‑26 |
| B‑28 | Endpoints datasets/EDA/limpieza | Harold | 5 | P1 | B‑15…B‑17 |
| B‑29 | Endpoints experimentos/modelos (estados, aprobación, publicación) | Harold | 5 | P1 | B‑23 |
| B‑30 | Predicción por lote + endpoints territoriales para EPS | Harold | 5 | P1 | B‑29 |
| B‑31 | Motor de reglas de alerta + estados + historial | Harold | 5 | P1 | B‑30, D‑11 |
| B‑32 | Admin: login, dashboard, datasets, carga masiva | Luis | 6 | P1 | B‑25 |
| B‑33 | Admin: formulario de ingreso territorial | Luis | 6 | P2 | B‑25 |
| B‑34 | Admin: páginas EDA, limpieza, selección, partición, entrenamiento, comparación, modelos | Luis + Diego | 6 | P1 | B‑25 |
| B‑35 | EPS: login, dashboard, consulta territorial | Luis | 7 | P1 | B‑25 |
| B‑36 | EPS: comparación poblacional y gráficos | Luis | 7 | P1 | B‑35 |
| B‑37 | EPS: mapa coroplético | Luis | 7 | P2 | B‑14 |
| B‑38 | EPS: alertas (lista, prioridad, observaciones, responsable, estados, historial) | Luis | 7 | P1 | B‑31 |
| B‑39 | EPS: exportación de informes | Luis | 7 | P2 | B‑36 |
| B‑40 | Docker Compose completo, pruebas E2E y de permisos | Harold | 8 | P1 | Todo |
| B‑41 | Manual técnico y manual de usuario; documento de limitaciones | Todos | 8 | P1 | Todo |

## 5. Definición de "terminado" para cualquier tarea

1. Código revisado por otro integrante (pull request).
2. Pruebas automatizadas que pasan.
3. Documentación de funciones públicas.
4. Sin datos reales ni secretos en Git.
5. Registro en `PROJECT_PROGRESS.md`.
