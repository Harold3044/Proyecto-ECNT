# API REST — Plataforma ECNT

FastAPI + SQLAlchemy (SQLite por defecto; PostgreSQL con `ECNT_DATABASE_URL`). Documentación interactiva en `http://localhost:8000/docs` (OpenAPI).

```bash
uvicorn ecnt_api.main:app --reload --port 8000
python scripts/cargar_datos_iniciales.py --aprobar-y-publicar   # datos reales + modelo publicado
```

## Autenticación
`POST /auth/login` (formulario `username`, `password`) devuelve un token JWT (`Authorization: Bearer …`), vigente 120 min. Las contraseñas se guardan con bcrypt. **Los permisos se verifican en el servidor**, no solo en la interfaz.

Usuarios iniciales de desarrollo (cámbielos en `.env`): `admin@ecnt.local`, `investigador@ecnt.local`, `eps@ecnt.local`.

## Matriz de permisos

| Recurso | admin | investigador | eps |
|---|:-:|:-:|:-:|
| Usuarios (`/users`), auditoría (`/audit`) | ✔ | — | — |
| Datasets, EDA, limpieza, selección de variables (`/datasets/*`) | ✔ | ✔ | — |
| Entrenar y comparar (`/experiments/*`), consultar modelos, predecir datos nuevos | ✔ | ✔ | — |
| **Aprobar / publicar / retirar modelos** | ✔ | — | — |
| Reglas de alerta (crear/editar), generar alertas | ✔ | — | — |
| Dashboard, territorios, comparación, exportación | ✔ | ✔ | ✔ |
| Consultar y gestionar alertas (estado, prioridad, responsable, observaciones) | ✔ | ✔ | ✔ |
| Catálogos (`/catalog/*`), modelo publicado (`/models/published`) | ✔ | ✔ | ✔ |

## Endpoints principales

| Módulo | Método y ruta | Descripción |
|---|---|---|
| Datasets | `POST /datasets/upload` | Carga masiva CSV/Excel; valida y rechaza (422) sin guardar si hay errores bloqueantes |
| | `POST /datasets/validate` | Vista previa y validación sin guardar |
| | `POST /datasets/form` · `POST /datasets/versions/{id}/records` | Ingreso individual por formulario (crea una nueva versión) |
| | `GET /datasets` · `GET /datasets/{id}` · `GET /datasets/versions/{id}` | Historial, versiones y linaje |
| | `GET /datasets/versions/{id}/rows` · `/download` | Datos paginados / CSV |
| EDA | `GET /datasets/versions/{id}/eda` | Calidad, validación y estadística descriptiva |
| | `GET …/eda/frequencies?column=` · `…/eda/correlation` · `…/eda/plot?kind=` | Frecuencias, correlaciones y gráficos (JSON de Plotly) |
| Limpieza | `POST /datasets/versions/{id}/clean` | Pasos declarativos → nueva versión; el original no cambia |
| Variables | `POST /datasets/versions/{id}/features` | Ranking, VIF y OLS **solo con entrenamiento** |
| Experimentos | `POST /experiments` · `POST /experiments/compare` | Entrenar uno / comparar varios con la misma partición |
| | `GET /experiments/{id}` · `/plots` · `GET /experiments/groups/{g}` | Resultados, gráficos y selección |
| Modelos | `GET /models` · `GET /models/{id}` · `GET /models/compare?ids=` | Versiones y comparación |
| | `POST /models/{id}/approve` (justificación) → `POST /models/{id}/publish` → `POST /models/{id}/retire` | Ciclo de vida con aprobación humana |
| | `POST /models/{id}/predict` · `POST /models/{id}/predict-version/{v}` | Pruebas con datos nuevos (métricas si traen el objetivo) |
| EPS | `GET /dashboard` · `GET /territories` · `GET /territories/{divipola}` · `GET /territories/compare?ids=` · `GET /territories/export` | Consulta territorial |
| Alertas | `GET/POST/PATCH /alert-rules` · `POST /alerts/generate` · `GET /alerts` · `GET/PATCH /alerts/{id}` | Reglas, generación, seguimiento e historial |

## Reglas de negocio implementadas
- **Ciclo del modelo**: `evaluado → aprobado → publicado → retirado`. Solo se publica un modelo aprobado (con justificación). Publicar un modelo retira el publicado anterior del mismo objetivo. La línea base nunca se aprueba.
- **Predicciones para la EPS**: precalculadas al publicar, versionadas, y **fuera de muestra** (CV de 5 pliegues) para los territorios con valor observado, de modo que la comparación observado/esperado no esté sesgada por el sobreajuste.
- **Alertas**: reglas configurables con justificación obligatoria; no se duplican alertas abiertas; transiciones de estado validadas; cerrar o descartar exige una observación; asignar exige un responsable; historial inmutable de eventos.
- **Privacidad**: rechazo de columnas con datos personales; conteos de defunciones menores a `ECNT_MIN_CELL_SIZE` (10) se suprimen para el rol EPS.
- **Auditoría** de inicios de sesión, cargas, limpiezas, entrenamientos, aprobaciones, publicaciones, exportaciones y cambios de alertas.
