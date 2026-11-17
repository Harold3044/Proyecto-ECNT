# PROJECT_PROGRESS — Plataforma ECNT (Grupo 05)

## Estado actual

| Campo | Valor |
|---|---|
| Fase actual | **Bloque A (F1 + F2): COMPLETADO, en espera de aprobación** |
| Fases completadas | 0, 1, 2 (el Bloque A está pendiente de aprobación) |
| Próxima actividad autorizada | Ninguna. Se requiere autorización explícita para el Bloque B (F3 + F4). |
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

## Módulos implementados

- `ecnt_core.config`, `ecnt_core.sources.dane` (NBI, defunciones, población, tasa estandarizada por edad).
- `ecnt_api.main` (solo `/health`).
