# Manual técnico — Plataforma ECNT

## 1. Arquitectura

```
 [App Administrador · Streamlit :8501] ─┐
                                        ├─ REST + JWT ─> [API FastAPI :8000] ─┬─> SQLite / PostgreSQL
 [App EPS · Streamlit :8502] ───────────┘                     │               └─> data/storage (versiones Parquet, modelos .joblib)
                                                              └─> ecnt_core (EDA, limpieza, ML)
```

| Paquete | Ruta | Rol |
|---|---|---|
| `ecnt_core` | `src/ecnt_core/` | Ciencia de datos sin dependencias web (ver `docs/MOTOR_DATOS_ML.md`) |
| `ecnt_api` | `src/ecnt_api/` | API REST, persistencia, seguridad, reglas de negocio (ver `docs/API.md`) |
| `ecnt_client` | `src/ecnt_client/` | Cliente HTTP y utilidades de interfaz; único contacto de las apps con la API |
| Apps | `apps/admin/`, `apps/eps/` | Interfaces Streamlit independientes |

Decisiones de arquitectura: `docs/ARQUITECTURA.md` y `docs/DECISIONES.md`.

## 2. Requisitos
- Python 3.12 o superior (probado con 3.13.13). Docker opcional (probado con 29.2.1).
- Unos 2 GB de disco (las fuentes DANE ocupan ~250 MB y la imagen Docker ~1,4 GB).

## 3. Instalación local

```bash
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.lock.txt      # versiones exactas
pip install -r requirements-dev.txt       # pruebas y linter
pip install -e .
copy .env.example .env                    # defina ECNT_JWT_SECRET y las contraseñas
```

## 4. Datos (reproducibles desde fuentes oficiales)
1. Descargue las fuentes indicadas en `data/README.md` y `docs/datos/FUENTE_*.md`.
2. `python scripts/construir_dataset_caribe.py`: genera `data/processed/` y `manifiesto.json` con las huellas.
3. `python scripts/cargar_datos_iniciales.py --aprobar-y-publicar`: carga los datos en la plataforma, compara 5 modelos y (con el indicador) aprueba y publica el recomendado.

## 5. Ejecución

| Modo | Comando |
|---|---|
| Local (Windows, 3 servicios) | `powershell -ExecutionPolicy Bypass -File scripts\iniciar_plataforma.ps1` |
| Local manual | `uvicorn ecnt_api.main:app --port 8000` · `streamlit run apps/admin/app.py --server.port 8501` · `streamlit run apps/eps/app.py --server.port 8502` |
| Docker | Defina `ECNT_JWT_SECRET` en `.env` y ejecute `docker compose up --build` |

Docker Compose levanta 3 contenedores con la misma imagen; `./data` se monta como volumen; las apps llegan a la API por la red interna (`http://api:8000`). Para usar otros puertos del host: `ECNT_API_PORT`, `ECNT_ADMIN_PORT`, `ECNT_EPS_PORT`.

## 6. Configuración (`.env`, prefijo `ECNT_`)

| Variable | Uso | Defecto |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy (`sqlite:///…` o `postgresql+psycopg://…`, este último requiere instalar `psycopg`) | SQLite en `data/storage/ecnt.db` |
| `STORAGE_DIR` | Versiones de datasets y modelos | `data/storage` |
| `JWT_SECRET`, `JWT_EXPIRE_MINUTES` | Firma y duración de sesiones | Valor de desarrollo + advertencia |
| `BOOTSTRAP_*_EMAIL/PASSWORD` | Usuarios creados en el primer arranque (solo si la BD no tiene usuarios) | Ver README |
| `MIN_CELL_SIZE` | Supresión de conteos pequeños para la EPS | 10 |
| `API_URL` | URL de la API para las apps (use `127.0.0.1`, no `localhost`, en Windows) | `http://127.0.0.1:8000` |

## 7. Pruebas y calidad

```bash
pytest                  # 129 pruebas (cobertura 88 %): núcleo, API, permisos, interfaces de extremo a extremo
ruff check src tests scripts apps
pip-audit -r requirements.lock.txt
python scripts/prueba_rendimiento.py --url http://127.0.0.1:8000
```

| Suite | Contenido |
|---|---|
| `test_sources_dane.py` | Lectores DANE, tasa estandarizada, cuadre con totales oficiales |
| `test_processing.py` | Lectura, validación, EDA, limpieza con linaje |
| `test_ml.py` | Partición, selección sin fuga, modelos, regla de 1 EE, registro, datos nuevos |
| `test_api.py` | Integración de la API con BD temporal |
| `test_permissions.py` | Matriz de permisos por rol, tokens manipulados o vencidos, usuarios desactivados |
| `test_apps_e2e.py` | API real (uvicorn) + cada vista de ambas apps con `AppTest`, incluidas interacciones |

## 8. Operación
- **Respaldo**: copiar `data/storage/` (BD, versiones y modelos) y `data/processed/manifiesto.json`.
- **Nuevo modelo**: entrenar en la app Administrador → aprobar con justificación → publicar. Publicar retira el anterior y regenera las predicciones y alertas.
- **Auditoría**: menú Administración → Auditoría, o `GET /audit`.
- **Registros**: uvicorn y Streamlit escriben en la salida estándar (`docker compose logs api`).

## 9. Rendimiento medido (2026-11-17, 200 peticiones, 10 concurrentes, datos reales)

| Endpoint | Local p50 / p95 (ms) | Docker en Windows p50 / p95 (ms) |
|---|---|---|
| `/health` | 12 / 18 | 36 / 61 |
| `/dashboard` | 334 / 373 | 1.402 / 1.668 |
| `/territories?con_determinantes=true` | 349 / 414 | 1.260 / 1.551 |
| `/territories/{divipola}` | 91 / 119 | 292 / 418 |
| `/alerts` | 120 / 180 | 524 / 796 |

Todas las peticiones fueron exitosas (200/200). Una petición aislada de `/dashboard` tarda unos 25 ms una vez cargada la caché. La diferencia con Docker se debe a SQLite sobre una carpeta montada de Windows. Datos completos en `reports/rendimiento_local.json` y `reports/rendimiento_docker.json`.
