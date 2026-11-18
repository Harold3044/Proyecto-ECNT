# Guía de demostración en vivo (≈ 12 minutos)

Archivos en `data/demo/` (se regeneran con `python scripts/generar_datos_demo.py`):

| Archivo | Contenido | Para qué |
|---|---|---|
| `DEMO_1_caribe_para_cargar.csv` | 197 municipios REALES del Caribe (DANE) + **3 filas duplicadas** (Valledupar, Cartagena, Uribia) y **4 celdas vacías** introducidas a propósito (`nbi_resto` en Montería y Santa Marta; `comp_servicios_cab` en Sincelejo y Barranquilla) | Mostrar carga, validación, EDA, limpieza, entrenamiento |
| `DEMO_2_datos_nuevos_otras_regiones.xlsx` | 40 municipios REALES de 20 departamentos fuera del Caribe, con su mortalidad registrada | Mostrar predicción con datos nuevos (y la carga de Excel) |

> Ningún valor fue inventado: solo se duplicaron filas y se vaciaron celdas para tener algo que limpiar.

**Antes de empezar:** ejecute `scripts\iniciar_plataforma.ps1` y abra http://localhost:8501 (Administrador) y http://localhost:8502 (EPS) en dos pestañas.

## Parte 1 · Ambiente Administrador (`admin@ecnt.local` / `Admin2026!`)

1. **Dashboard**: el banner, las tarjetas y el modelo publicado actual.
2. **Carga masiva** → suba `DEMO_1_caribe_para_cargar.csv`.
   - Vista previa e identificación de columnas.
   - Validación: **válido**, con advertencias de *filas duplicadas* (las 3 introducidas) y *constante* (`periodo`, `region` y `es_sintetico` tienen un solo valor, lo cual es normal).
   - Nombre: `Demo Caribe`, fuente: `DANE`, uso: **modelado** → **Cargar dataset** (versión v1, 200 filas).
3. **Análisis estadístico** → elija *Demo Caribe*.
   - Tarjetas: 200 registros, **3 filas duplicadas**, **4 celdas nulas**.
   - *Descriptivas*: la columna **nombre** explica cada variable; abra *¿Qué significa cada variable?*.
   - *Distribuciones*: `tasa_mort_ecnt_std` (objetivo) y, agrupada por `departamento`, el diagrama de caja.
   - *Correlaciones*: la ruralidad (`pct_poblacion_resto`) aparece primero con signo **negativo** (hallazgo de subregistro).
4. **Limpieza de datos** → *Demo Caribe* v1.
   - Paso 1: `drop_duplicates` sin llave → **Agregar paso**.
   - Paso 2: `impute`, columnas `nbi_resto` y `comp_servicios_cab`, estrategia `median` → **Agregar paso**.
   - La **vista previa** muestra 200 → 197 filas, sin advertencias. **Aplicar y crear versión** → v2. El original v1 se conserva.
   - (Opcional, para mostrar la protección) `drop_duplicates` con llave `periodo` → la vista previa advierte que se perdería el 99 % de las filas.
5. **Selección de variables** → *Demo Caribe* **v2**, 80/20, semilla 42 → **Calcular relevancia**: ranking, VIF (colinealidad alta entre NBI total, cabecera y resto) y regresión OLS, solo con entrenamiento.
6. **Entrenamiento** → *Demo Caribe* **v2**.
   - Partición **80/20**, semilla **42**, estrategia aleatoria.
   - Selección automática: **Top k del ranking**, k = **8**.
   - Algoritmos: los cinco. **Entrenar** (≈ 20–30 s).
   - Resultado esperado: **Random Forest recomendado** (RMSE CV ≈ 47, R² prueba ≈ 0,30), con la explicación de la regla de un error estándar.
7. **Comparación** → elija el grupo recién creado; en *Detalle de un experimento* vea real vs. predicho, residuos, importancia de variables y errores por departamento.
8. **Gestión de modelos** → elija el Random Forest nuevo.
   - **Aprobar**, con la justificación: *Supera la línea base y cumple la regla de un error estándar.*
   - **Publicar** → 197 predicciones y alertas nuevas. El modelo anterior queda **retirado** automáticamente.
9. **Predicción** → modelo publicado → *Subir archivo* → `DEMO_2_datos_nuevos_otras_regiones.xlsx` → **Predecir**.
   - Métricas independientes (R² ≈ 0,04): **el modelo casi no transfiere a otras regiones**, como se dijo en la presentación.
10. (Opcional) **Ingreso territorial** → *Crear un dataset nuevo*: DIVIPOLA `20013`, municipio `AGUSTÍN CODAZZI`, departamento `CESAR`, `nbi_total` 40,5 → **Guardar registro**.
11. (Opcional) **Auditoría**: quedaron registradas la carga, la limpieza, el entrenamiento, la aprobación y la publicación.

## Parte 2 · Ambiente EPS (`eps@ecnt.local` / `Eps2026!`)

1. **Panel principal**: 197 territorios, municipios en riesgo alto, alertas, población rural, dona por nivel, barras por departamento y evolución 2018–2021.
2. **Territorios**: directorio ordenado por riesgo; filtre por *muy alto*; busque `URIBIA` o `MANAURE` → ficha territorial con la mortalidad registrada muy por debajo de la esperada.
3. **Mapa**: nivel de riesgo por municipio.
4. **Alertas**: filtre por prioridad **alta**; en *Seguimiento* elija una alerta → estado **asignada**, responsable `Coordinación de salud pública`, observación → **Registrar**; el historial muestra el cambio.
5. **Diccionario de variables** e **Informes** (descarga CSV).

## Si algo falla en vivo

| Síntoma | Solución |
|---|---|
| "No se pudo conectar con la API" | La ventana de la API está cerrada: vuelva a ejecutar `iniciar_plataforma.ps1` |
| El menú lateral no aparece | Pulse **»** arriba a la izquierda |
| La EPS dice que no hay modelo publicado | Repita los pasos 8 (aprobar y publicar) |
| Un archivo propio no carga | Lea el reporte de validación: los errores típicos son un DIVIPOLA que no tiene 5 dígitos, una columna con nombre de dato personal (documento, nombre, teléfono…) o la falta de la columna `divipola` |
