# Proyecto-ECNT

Proyecto de Aula de la asignatura Inteligencia Artificial en dónde se busca crear un sistema de predicción de riesgo de ECNT en poblaciones dispersas.

**Predicción de riesgo de enfermedades crónicas no transmisibles (ECNT) asociadas a determinantes sociales en población dispersa del Caribe colombiano** — Grupo 05 (Diego Nieves, Harold Solano, Luis Vivanco). Desarrollo de la plataforma: Harold Solano.

> **Unidad de análisis territorial.** La plataforma estima indicadores por municipio y periodo. No evalúa ni diagnostica personas.

## Arquitectura

```
 [App Administrador · Streamlit :8501] ─┐
                                        ├─ REST + JWT ─> [API FastAPI :8000] ─┬─> SQLite / PostgreSQL
 [App EPS · Streamlit :8502] ───────────┘                     │               └─> data/storage (archivos, modelos)
                                                              └─> ecnt_core (EDA, limpieza, ML)
```

| Carpeta | Contenido |
|---|---|
| `src/ecnt_core/` | Núcleo de ciencia de datos: carga, validación, EDA, limpieza, selección, partición, modelos, evaluación, registro |
| `src/ecnt_api/` | API REST (FastAPI): autenticación, roles, datasets, experimentos, modelos, predicciones, territorios, alertas |
| `apps/admin/` | Ambiente Administrador / Investigador |
| `apps/eps/` | Ambiente EPS (consulta, dashboard y alertas) |
| `scripts/` | Construcción reproducible de los datasets desde fuentes oficiales |
| `data/` | Datos locales (no versionados, salvo los sintéticos de prueba) |
| `docs/` | Arquitectura, decisiones, plan, fuentes de datos y manuales |
| `tests/` | Pruebas automatizadas |

Documentación: [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) · [docs/DECISIONES.md](docs/DECISIONES.md) · [docs/PLAN_DE_TRABAJO.md](docs/PLAN_DE_TRABAJO.md) · [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md)

## Instalación (Windows)

```bash
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .
copy .env.example .env      # edite los secretos
pytest
```

## Datos

Los archivos de datos no se suben a Git. Las fuentes oficiales y la forma de obtenerlas están en [docs/datos/](docs/datos/). Todo dato sintético lleva el prefijo `SINTETICO_` y la bandera `es_sintetico`.
