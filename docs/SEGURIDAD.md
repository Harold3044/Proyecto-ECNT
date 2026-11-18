# Evaluación de seguridad y tratamiento de datos (Bloque E)

Fecha: 2026-11-17. Alcance: API, aplicaciones, datos y despliegue.

## 1. Controles implementados y verificados

| Área | Control | Verificación |
|---|---|---|
| Autenticación | Contraseñas con bcrypt (sal por usuario); JWT HS256 con vencimiento (120 min) | `tests/test_permissions.py`: token forjado con otra clave → 401; token vencido → 401 |
| Autorización | Roles verificados **en el servidor** en cada endpoint; el rol se toma de la BD, no del token | Matriz de 40 endpoints × 3 roles + sin sesión (`test_matriz_de_permisos`); token con rol "admin" firmado para un usuario EPS → 403 |
| Cuentas | Desactivar un usuario revoca el acceso de inmediato; el admin no puede desactivarse a sí mismo | `test_usuario_desactivado_pierde_acceso`, `test_admin_no_puede_desactivarse_a_si_mismo` |
| Datos personales | Rechazo de columnas con nombres de identificadores personales (documento, nombre, teléfono, dirección, correo, historia clínica…); solo datos territoriales agregados | `test_rechaza_columnas_personales`, `test_carga_masiva_y_rechazo_de_datos_personales` (no se guarda nada) |
| Confidencialidad | Conteos de defunciones < 10 se suprimen para el rol EPS | Lógica en `services/territories.py` |
| Integridad de datos | Original inmutable; versiones con huella SHA‑256 y linaje | `test_eda_limpieza_y_original_inmutable` |
| Integridad de modelos | Huella SHA‑256 del `.joblib` verificada al cargar | `test_bundle_alterado_se_detecta` |
| Gobierno de modelos | Ningún modelo llega a la EPS sin aprobación humana con justificación; publicar retira el anterior | `test_flujo_aprobacion_publicacion_y_eps` |
| Entradas | Validación con Pydantic; extensiones y tamaño de archivo limitados (25 MB); rutas de almacenamiento confinadas (`Storage.abs`) | Pruebas de archivos inválidos |
| Inyección SQL | Solo consultas parametrizadas del ORM (SQLAlchemy); no hay SQL construido con texto | Revisión de código |
| Trazabilidad | Auditoría de inicio de sesión (incluidos fallidos), cargas, limpiezas, entrenamientos, aprobaciones, publicaciones, exportaciones y cambios de alertas | `test_auditoria` |
| Secretos | `.env` excluido de Git; advertencia al arrancar si se usan el secreto JWT o la contraseña por defecto; Docker Compose **exige** `ECNT_JWT_SECRET` | Verificado en los registros del contenedor |
| Dependencias | `pip-audit` sobre `requirements.lock.txt` | **Sin vulnerabilidades conocidas** (2026-11-17) |
| Contenedores | Usuario sin privilegios (`uid 1000`); `.dockerignore` excluye `.env`, datos y `.git` | Imagen construida y ejecutada |

## 2. Riesgos residuales (aceptados por el alcance académico)

| Riesgo | Mitigación recomendada para producción |
|---|---|
| Contraseñas iniciales de desarrollo conocidas (README) | Definirlas en `.env` antes del primer arranque; forzar cambio en el primer ingreso |
| Sin límite de intentos de inicio de sesión (fuerza bruta) | Limitar intentos por IP/usuario (p. ej. `slowapi`) o un proxy inverso |
| Tráfico HTTP sin cifrar | Publicar detrás de un proxy inverso con HTTPS (Caddy/Nginx) |
| Token en `session_state` de Streamlit sin renovación | Tokens cortos + renovación; cierre de sesión por inactividad |
| SQLite sin cifrado en reposo | PostgreSQL con cifrado de disco y copias de seguridad |
| La EPS ve todos los territorios del Caribe | Asociar territorios por EPS si hay varias (decisión D‑10) |
