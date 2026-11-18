# Manual de usuario — Plataforma ECNT

La plataforma estima, **por municipio**, la mortalidad por enfermedades crónicas no transmisibles (ECNT) cardiometabólicas esperada según los determinantes sociales. Sirve para priorizar acciones de salud pública. **No diagnostica personas.**

Hay dos aplicaciones:

| Aplicación | Dirección | Quién la usa |
|---|---|---|
| Administrador / Investigador | http://localhost:8501 | Equipo del proyecto: datos y modelos |
| EPS | http://localhost:8502 | EPS: consulta de resultados y seguimiento de alertas |

Ingrese con su correo y contraseña. Si su rol no corresponde a la aplicación, el sistema se lo indicará. Use **Cerrar sesión** en la barra lateral al terminar.

---

> **Diccionario de variables.** Si no entiende una variable, consulte `docs/datos/DICCIONARIO_VARIABLES.md`, la página
> **Diccionario de variables** del ambiente EPS, la pestaña **Diccionario de variables** en *Datasets*, o el desplegable
> *¿Qué significa cada variable?* en *Análisis estadístico*. En el formulario territorial, pase el cursor sobre el ícono
> de ayuda de cada campo.

## Parte A. Ambiente Administrador / Investigador

El flujo recomendado sigue el orden del menú:

1. **Carga masiva** (Datos → Carga masiva). Suba un CSV o Excel. El sistema muestra una vista previa, identifica las columnas y valida el archivo.
   - *Errores* (por ejemplo, códigos DIVIPOLA inválidos o columnas con datos personales) impiden la carga.
   - *Advertencias* (nulos, duplicados, valores fuera de rango) se pueden corregir después.
   - Indique la fuente y si los datos son **sintéticos**.
2. **Ingreso territorial** (Datos → Ingreso territorial). Registre un municipio y periodo campo por campo. Cada registro crea una nueva versión del dataset.
3. **Gestión de datasets**. Consulte el historial, las versiones, el linaje de transformaciones y la validación, y descargue cualquier versión.
4. **Estadística descriptiva** (Análisis). Incluye:
   - Media, mediana, moda, desviación, mínimos, máximos, cuartiles y atípicos.
   - Calidad: nulos, duplicados, rangos y tipos.
   - Distribuciones, frecuencias y correlaciones.
5. **Limpieza y transformación**. Agregue pasos (eliminar duplicados, imputar, convertir tipos, recortar atípicos, log, codificar…). Antes de aplicar, la **vista previa** muestra cuántas filas y columnas quedarían; si se perdería más del 20 % de las filas, el sistema lo advierte y pide confirmación (por ejemplo, eliminar duplicados usando como llave una columna de pocos valores). Se crea una versión nueva; el original no cambia.
6. **Selección de variables**. Elija la partición y la semilla, y calcule el ranking de relevancia, la colinealidad (VIF) y la regresión múltiple. Todo se calcula **solo con los datos de entrenamiento**.
7. **Partición y entrenamiento** (Modelos).
   - Elija la proporción de entrenamiento y prueba (70/30, 75/25, 80/20 o 90/10), la semilla y la estrategia (aleatoria o geográfica).
   - Elija las variables, la selección automática, los algoritmos y sus hiperparámetros. Pulse **Entrenar**.
   - El sistema compara los modelos con la misma partición y **recomienda** uno: debe superar a la línea base y, entre los mejores, se elige el más simple.
8. **Comparación de resultados**. Consulte MAE, RMSE y R² (validación cruzada y prueba), intervalos de confianza, real frente a predicho, residuos, importancia de variables y desempeño por departamento.
9. **Gestión de modelos** (solo el administrador aprueba y publica).
   - **Aprobar** exige una justificación.
   - **Publicar** pone el modelo a disposición de la EPS, calcula las predicciones de todos los territorios y genera las alertas. El modelo publicado anterior se retira automáticamente.
10. **Pruebas con datos nuevos**. Aplique un modelo a datos que no participaron en el entrenamiento: el dataset de validación externa o un archivo propio. Si los datos traen el valor observado, verá métricas independientes.
11. **Administración** (solo el administrador): reglas de alerta (umbrales, prioridad, activación y justificación obligatoria), usuarios (crear, activar o desactivar) y auditoría.

---

## Parte B. Ambiente EPS

1. **Dashboard**: territorios analizados, población, población rural dispersa y de centros poblados, tasa esperada, distribución por nivel (quintiles), evolución 2018–2021, departamentos y municipios con valores más altos, y alertas abiertas.
2. **Territorios**: directorio de municipios ordenados por riesgo, con buscador por nombre o DIVIPOLA, filtro por departamento y por nivel, y marcas de *exceso* o *posible subregistro*. Debajo, en la **ficha territorial**, elija un municipio. Verá:
   - **Nivel**: de *muy bajo* a *muy alto*, comparado con los demás municipios del Caribe.
   - **Mortalidad esperada** e **intervalo del 90 %**.
   - **Mortalidad registrada**: si está por debajo del intervalo, revise un posible **subregistro**; si está por encima, hay un exceso que amerita revisión.
   - Determinantes sociales frente a la mediana del Caribe, historial por año y alertas del municipio.
   - Los conteos menores a 10 defunciones se muestran como "suprimido".
3. **Análisis poblacional**: compare municipios (valores esperado y registrado), departamentos (distribución) y la relación entre cada determinante y la mortalidad.
4. **Mapa**: municipios ubicados en su cabecera. El tamaño representa la población y el color, el indicador elegido. Puede filtrar por departamento.
5. **Alertas**: filtre por estado, prioridad o departamento. Al seleccionar una alerta puede:
   - **Cambiar el estado**: nueva → en revisión → asignada → en seguimiento → cerrada (o descartada). Asignar exige un responsable; cerrar o descartar exige una observación.
   - Cambiar la **prioridad**, asignar un **responsable** y registrar **observaciones**.
   - Consultar el **historial** completo y la evidencia que originó la alerta.
6. **Diccionario de variables**: significado de cada indicador en lenguaje sencillo.
7. **Exportar informes**: descargue en CSV el informe territorial (todo el Caribe o un departamento) y las alertas.

### Tipos de alerta

| Alerta | Significado | Acción sugerida |
|---|---|---|
| Mortalidad esperada alta (quintil superior) | Los determinantes del municipio se asocian a la mayor mortalidad esperada | Priorizar acciones preventivas |
| Exceso de mortalidad observada | Lo registrado supera lo esperado más allá del intervalo del 90 % | Revisión epidemiológica |
| Posible subregistro | Lo registrado es muy inferior a lo esperado | Verificar la calidad del registro y el acceso a servicios; **no** interpretar como bajo riesgo |

> Las estimaciones son territoriales, asociativas y con incertidumbre. Ver `docs/LIMITACIONES.md`.
