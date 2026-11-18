# PROJECT_PROGRESS — Plataforma ECNT (Grupo 05)

## Estado actual

| Campo | Valor |
|---|---|
| Fase actual | **Bloque E (F8 integración, pruebas y despliegue): COMPLETADO — proyecto terminado, en espera de aprobación final** |
| Fases completadas | 0–7 (aprobadas); 8 (pendiente de aprobación) |
| Próxima actividad autorizada | Ninguna. |
| Última actualización | 2026-11-17 |

## Registro por fase

### Fase 0 — Inspección y planificación (2026-11-17)

**Actividades**
- Inspección de `Proyecto-ECNT/` (vacío, sin Git) y de la carpeta padre (solo lectura).
- Revisión de la propuesta de proyecto (Fases 1–2), del dataset de 2.316 registros y del proyecto previo `fase2-ecnt-caribe`.
- Verificación de herramientas instaladas (Python 3.13, Node 26, Docker 29, Git 2.53; sin PostgreSQL local).
- Propuesta de arquitectura, estructura, plan, backlog, decisiones y riesgos.

**Archivos creados**
- `PROJECT_PROGRESS.md`
- `docs/INVENTARIO_INICIAL.md`
- `docs/ARQUITECTURA.md`
- `docs/DECISIONES.md`
- `docs/PLAN_DE_TRABAJO.md`

**Archivos modificados / eliminados**: ninguno.

**Pruebas ejecutadas**: no aplica (fase sin código). Se ejecutaron solo lecturas de archivos para el inventario.

**Hallazgos principales**
- No hay variable objetivo de salud real en ningún material existente; los resultados previos usan datos simulados.
- Predictores reales disponibles: NBI CNPV 2018 municipal (total / cabecera / resto) y microdatos censales solo del Cesar.

**Errores pendientes**: ninguno de código. Pendiente abrir `ano-corrido-CUADRO5-NOFETALES-2018-PRELIMINAR.xls` (requiere `xlrd`), en Fase 2.

**Decisiones tomadas**: ninguna aprobada aún. Propuestas AD‑01 a AD‑08 en `docs/DECISIONES.md`.

**Decisiones pendientes**: D‑01 a D‑11 en `docs/DECISIONES.md`.

### Fase 0 — Replanificación (2026-11-17)
- Entrega el 19‑nov, desarrollador único y repositorio nuevo. Plan comprimido en 5 bloques (A–E), con recortes de alcance documentados.
- Archivos modificados: `docs/PLAN_DE_TRABAJO.md` (sección 0), `docs/DECISIONES.md` (AD‑09 a AD‑12 y respuestas), `docs/ARQUITECTURA.md` (nota de ajuste).

- Decisión del usuario: aprobaciones por **5 bloques (A–E)**, con informe de 10 puntos al cierre de cada bloque.
- Decisión del usuario: variable objetivo **real si se puede** (mortalidad por ECNT del DANE, máximo ~1 h de investigación); si no, **sintética marcada** y documentada como limitación. Predictores reales: NBI CNPV 2018.

### Bloque A — F1 Preparación + F2 Datos (2026-11-17)

**F1**
- Git conectado a `https://github.com/Harold3044/Proyecto-ECNT.git` sobre el commit inicial remoto (se conservó el texto del README original).
- Entorno `.venv` (Python 3.13.13); `requirements.txt`, `requirements-dev.txt`, `requirements.lock.txt` (versiones exactas).
- `pyproject.toml` (paquete instalable con diseño `src/`, pytest, ruff), `.gitignore` (excluye datos, `.env`, modelos, BD), `.env.example`, README.
- API mínima `GET /health`.

**F2**
- Fuentes descargadas del DANE: proyecciones de población municipal 2018–2042 y Cuadro 5 de defunciones definitivas 2018–2021.
- Lectores en `src/ecnt_core/sources/dane.py`; ETL reproducible `scripts/construir_dataset_caribe.py`.
- Datasets reales: `caribe_modelado.csv` (197 municipios) y `caribe_panel_municipio_anio.csv` (788 filas), más `manifiesto.json` con hashes.
- Variable objetivo propuesta: mortalidad por ECNT cardiometabólicas estandarizada por edad, 2018–2019 (`docs/datos/ESTRATEGIA_DATOS.md`).

**Pruebas**: `pytest` → 10 aprobadas (incluye la validación contra los totales oficiales del DANE). `ruff check` → sin errores.

**Errores corregidos durante el bloque**: lectura de encabezados con pandas 3 (NaN en tipo `str`); "TOTAL"/"Total" en el cuadro 2021; cuadros 2019+ protegidos (se desprotegen con la clave estándar de Excel).

**Pendiente**: aprobación de la variable objetivo y de los hallazgos H‑1 (relación inversa por posible subregistro) y H‑2 (conteos pequeños).

- Aprobado por el usuario (2026-11-17): variable objetivo `tasa_mort_ecnt_std` y Bloque A.

### Bloque B — F3 Procesamiento + F4 Machine Learning (2026-11-17)

**F3**: `schemas`, `io`, `validation`, `eda`, `cleaning` (14 operaciones con linaje), `plots`.
**F4**: `splitting` (4 estrategias, 4 proporciones, semilla), `features` (ranking, VIF, OLS), `models` (línea base, lineal, Ridge, RF, GB), `evaluation` (CV, bootstrap, intervalos, por grupo, regla de 1 EE), `experiment`, `registry` (joblib + SHA‑256 + predicción sobre datos nuevos).
**ETL ampliado**: `externo_otras_regiones_modelado.csv` (917 municipios reales fuera del Caribe) para validación externa.
**Experimento real**: `scripts/experimento_base.py` → `reports/experimento_base/` (ver su README). Elegido: Random Forest, RMSE de prueba 46,9 y R² 0,33 (IC 95 % de R²: −0,01 a 0,52); mejora del 14 % sobre la línea base; validación externa R² 0,08.

**Pruebas**: 47 aprobadas (`pytest`), cobertura de `ecnt_core` 82 %; `ruff` sin errores.
**Archivos nuevos**: `src/ecnt_core/{schemas,io,validation,eda,cleaning,plots,splitting,features,models,evaluation,experiment,registry}.py`, `tests/{conftest,test_processing,test_ml}.py`, `scripts/experimento_base.py`, `docs/MOTOR_DATOS_ML.md`, `reports/experimento_base/*`.
**Modificados**: `scripts/construir_dataset_caribe.py` (todo el país), `pyproject.toml` (largo de línea 120).

- Aprobado por el usuario (2026-11-17): Bloque B, recomendación de modelo (RF con selección de variables) y criterios de alerta.

### Bloque C — F5 Backend y API (2026-11-17)

- `src/ecnt_api/`: `config`, `db`, `orm` (10 tablas), `security` (bcrypt + JWT + roles), `utils` (JSON seguro, auditoría, almacenamiento), `services/{datasets,modeling,alerts,territories}`, `routers/{auth,catalog,datasets,experiments,models,territories,alerts}`, `main` (fábrica, errores, arranque, `/audit`).
- `scripts/cargar_datos_iniciales.py`: carga los 3 datasets reales, compara 5 modelos y, con `--aprobar-y-publicar`, aprueba y publica el elegido (Random Forest, modelo 4: 197 predicciones, 62 alertas).
- `docs/API.md`: endpoints, matriz de permisos y reglas de negocio.
- **Error corregido**: `normalize_codes` rellenaba con ceros códigos inválidos ("123" → "00123"); ahora solo restaura el cero inicial que Excel elimina (4 → 5 dígitos).

**Pruebas**: 62 aprobadas (16 de integración de la API con BD temporal), cobertura total 87 %; `ruff` sin errores. Prueba manual con servidor real (`uvicorn`): login EPS, dashboard, detalle territorial y 403 a `/datasets` para EPS.

- Aprobado por el usuario (2026-11-17): Bloque C; autorizado el Bloque D con un intento de 30 min para el mapa.

### Bloque D — F6 Ambiente Administrador + F7 Ambiente EPS (2026-11-17)

- **Mapa**: coordenadas oficiales DIVIPOLA (datos.gov.co, recurso `gdxc-w37w`), 197/197 municipios; resuelto en unos 5 min. Mapa de burbujas por cabecera municipal (no polígonos).
- `src/ecnt_client/`: cliente HTTP (único punto de contacto con la API) y utilidades de interfaz.
- `apps/admin/` (puerto 8501): inicio, datasets, carga masiva con vista previa y validación, formulario territorial, estadística descriptiva, limpieza, selección de variables, partición y entrenamiento, comparación, gestión de modelos (aprobar/publicar/retirar), pruebas con datos nuevos, reglas de alerta, usuarios, auditoría.
- `apps/eps/` (puerto 8502, independiente): dashboard, consulta territorial, análisis poblacional, mapa, alertas con seguimiento, exportación de informes.
- API: `/territories?con_determinantes=true`, coordenadas en las respuestas territoriales, `parametros` por algoritmo en `/experiments/compare`.
- `scripts/iniciar_plataforma.ps1`.
- **Error de diseño corregido** (lo detectó una prueba): con hiperparámetros manuales, la interfaz entrenaba modelos por separado y se perdía la selección comparativa; ahora `/experiments/compare` acepta hiperparámetros por algoritmo.

**Pruebas**: 85 aprobadas (incluye 23 de extremo a extremo de las interfaces: API real con uvicorn y cada vista renderizada con `AppTest`, más entrenamiento y seguimiento de alerta interactivos). Verificación con datos reales: las 12 vistas renderizan sin excepciones. Arranque real de los tres servicios comprobado (salud OK). `ruff` sin errores.

- Aprobado por el usuario (2026-11-17): Bloque D; autorizado el Bloque E.

### Bloque E — F8 Integración, pruebas y despliegue (2026-11-17)

- **Docker**: `Dockerfile` (imagen única, usuario sin privilegios), `.dockerignore`, `docker-compose.yml` (api, admin, eps; volumen `./data`; puertos configurables; `ECNT_JWT_SECRET` obligatorio). Construido y ejecutado con datos reales: API sana; las apps se conectan por la red interna.
- **Permisos**: `tests/test_permissions.py`, matriz de 40 endpoints × 3 roles + sin sesión, tokens manipulados o vencidos, rol elevado en el token, usuarios desactivados.
- **Seguridad**: `pip-audit` sin vulnerabilidades; advertencias al arrancar con secretos por defecto; `docs/SEGURIDAD.md`.
- **Rendimiento**: `scripts/prueba_rendimiento.py` → `reports/rendimiento_local.json` y `reports/rendimiento_docker.json`. Optimizaciones en `services/territories.py` (consulta por columnas, caché del panel, agregaciones vectorizadas).
- **Corrección importante**: la URL por defecto de las apps pasó de `localhost` a `127.0.0.1` (en Windows añadía ~2 s por petición).
- **Documentación**: `docs/manuales/MANUAL_TECNICO.md`, `docs/manuales/MANUAL_USUARIO.md`, `docs/LIMITACIONES.md`, `docs/INFORME_FINAL.md`.

**Pruebas**: 129 aprobadas, cobertura 88 % (`ecnt_core`, `ecnt_api`, `ecnt_client`); `ruff` sin errores.

## Módulos implementados

- `ecnt_core`: config, sources.dane, schemas, io, validation, eda, cleaning, plots, splitting, features, models, evaluation, experiment, registry.
- `ecnt_api`: API completa (autenticación, roles, datasets, EDA, limpieza, variables, experimentos, modelos, predicción, territorios, alertas, auditoría).
