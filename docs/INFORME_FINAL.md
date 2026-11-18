# Informe final de funcionamiento

**Proyecto:** Predicción de riesgo de enfermedades crónicas no transmisibles asociadas a determinantes sociales en población dispersa del Caribe colombiano.
**Grupo 05** · Inteligencia Artificial · Universidad Popular del Cesar. Desarrollo de la plataforma: Harold Solano.
**Fecha:** 17 de noviembre de 2026 · Repositorio: https://github.com/Harold3044/Proyecto-ECNT

## 1. Resultado

La plataforma es funcional y se despliega con un comando. Tiene dos ambientes independientes (Administrador/Investigador y EPS) que se comunican con una API REST con autenticación, roles, versionado de datos y modelos, aprobación humana y alertas con seguimiento. Usa **datos oficiales reales del DANE**, sin datos inventados. Los datos sintéticos solo se usan en las pruebas automáticas y están marcados como tales.

## 2. Datos y variable objetivo

| Elemento | Definición |
|---|---|
| Unidad de análisis | Municipio de la región Caribe (197), periodo 2018–2019 |
| Variable objetivo | Mortalidad por ECNT cardiometabólicas (lista 6/67 OPS: 302, 303, 304, 306, 307, 309, 601), estandarizada por edad (población de Colombia 2018), por 100.000 hab. |
| Predictores | NBI CNPV 2018 (total, cabecera y centros poblados/rural disperso: NBI, miseria, vivienda, servicios de agua y saneamiento, hacinamiento, inasistencia escolar, dependencia económica) y demografía (población, % rural, % ≥65 años, % 0–14 años) |
| Fuentes | DANE: NBI CNPV 2018; proyecciones de población municipal por área, sexo y edad; Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas 2018–2021); DIVIPOLA (coordenadas) |
| Validación de datos | Los totales departamentales coinciden exactamente con los publicados por el DANE (prueba automática) |

La fórmula originalmente propuesta (personas únicas con ECNT en RIPS / población rural dispersa) **no pudo construirse con fuentes accesibles**. La justificación está en `docs/datos/ESTRATEGIA_DATOS.md`.

## 3. Resultados del modelado (datos reales)

Partición 80/20 estratificada (semilla 42; 157 municipios de entrenamiento y 40 de prueba); validación cruzada 5 × 3 en entrenamiento; las 8 mejores variables del ranking, elegidas solo con entrenamiento; ajuste de hiperparámetros por rejilla.

| Modelo | RMSE CV | RMSE prueba | R² prueba |
|---|---|---|---|
| Línea base (media) | 54,69 | 57,17 | 0,00 |
| Regresión lineal múltiple | 51,39 | 49,26 | 0,26 |
| Ridge | 50,73 | 48,96 | 0,27 |
| **Random Forest (publicado)** | 47,20 | 47,80 | **0,30** |
| Gradient Boosting | 45,76 | 48,36 | 0,28 |

- **Criterio de selección**: superar a la línea base y elegir el modelo más simple dentro de 1 error estándar del mejor RMSE de validación cruzada. Así se eligió Random Forest sobre Gradient Boosting. El conjunto de prueba no intervino en la elección.
- **Mejora** sobre la línea base: 13,7 % en RMSE de validación cruzada.
- **Validación externa** con 917 municipios de otras regiones: R² 0,08. El modelo es específico del contexto Caribe.
- **Hallazgo principal**: la mortalidad *registrada* es menor en los municipios más rurales y pobres, coherente con subregistro. La plataforma lo convierte en la alerta "posible subregistro". Por ejemplo, Uribia (La Guajira) registra 18,5 frente a 102,1 esperado.

## 4. Funcionalidades entregadas

| Requerimiento | Estado |
|---|---|
| Ingreso individual (formulario territorial) y carga masiva (CSV/Excel) con validación, identificación de columnas, origen e historial | ✔ |
| Análisis exploratorio: media, mediana, moda, desviación, mín/máx, frecuencias, distribuciones; nulos, duplicados, inconsistencias, rangos, tipos e información insuficiente; gráficos | ✔ |
| Limpieza y transformación con versiones; el original se conserva | ✔ |
| Selección de variables (correlación, análisis estadístico, importancia, métodos de selección, interpretabilidad), sin fuga de información | ✔ |
| Partición 70/30, 75/25, 80/20, 90/10 con semilla; validación cruzada; partición geográfica, agrupada y temporal | ✔ |
| Regresión múltiple, Gradient Boosting y Random Forest (además de Ridge y la línea base) con hiperparámetros configurables y experimentos guardados | ✔ |
| MAE, RMSE, R², gráficos comparativos, real vs. predicho, residuos, desempeño por departamento, selección metodológica | ✔ |
| Pruebas con datos nuevos con transformaciones automáticas | ✔ |
| Gestión de modelos: versiones, comparación, aprobación, publicación e historial; sin reemplazo automático | ✔ |
| EPS: dashboard, consulta territorial, análisis poblacional, mapa, alertas (prioridad, observaciones, responsables, estados, historial) y exportación | ✔ |
| Autenticación, roles y auditoría | ✔ |
| Docker | ✔ (probado) |

## 5. Verificación

| Prueba | Resultado |
|---|---|
| Pruebas automatizadas (`pytest`) | **129 aprobadas**, cobertura 88 % |
| Matriz de permisos (40 endpoints × 3 roles + sin sesión) | Sin accesos indebidos |
| Interfaces de extremo a extremo (API real + 20 vistas + 2 flujos interactivos) | Sin errores |
| Auditoría de dependencias (`pip-audit`) | Sin vulnerabilidades conocidas |
| Linter (`ruff`) | Sin errores |
| Docker Compose (3 contenedores, datos reales) | API sana; las apps se conectan por la red interna; dashboard con 197 territorios |
| Rendimiento local (10 usuarios concurrentes) | 200/200 exitosas; dashboard p50 334 ms; detalle territorial p50 91 ms |

## 6. Problemas encontrados y corregidos durante el desarrollo

1. Los cuadros del DANE de 2019 en adelante venían protegidos con la clave estándar de Excel, y el de 2021 usa "Total" en lugar de "TOTAL".
2. Un código DIVIPOLA inválido ("123") se "corregía" en silencio a "00123". Ahora se reporta como inválido.
3. La comparación de modelos con hiperparámetros manuales perdía la selección comparativa.
4. En Windows, `localhost` añadía unos 2 s por petición (primero intenta IPv6). Ahora se usa `127.0.0.1`.
5. El dashboard y el listado territorial eran lentos con muchos usuarios simultáneos. Se optimizaron con consultas por columnas y caché del panel.

## 7. Limitaciones

Ver `docs/LIMITACIONES.md`. En resumen:
- Mide mortalidad registrada, no prevalencia.
- No se separa el rural disperso puro.
- Diseño transversal con n = 197.
- Capacidad predictiva modesta (R² ≈ 0,3).
- Subregistro probable en zonas dispersas.
- Asociación, no causalidad.

## 8. Trabajo futuro

1. Integrar los microdatos de Estadísticas Vitales con **área de residencia** para calcular la mortalidad en rural disperso puro.
2. Obtener acceso institucional a los **cubos SISPRO/RIPS** para estimar personas atendidas con ECNT.
3. Añadir determinantes **anuales** (IRCA, cobertura educativa, aseguramiento) para hacer predicción temporal.
4. Suavizado bayesiano empírico para municipios pequeños.
5. Ponderar por población en el entrenamiento.
6. Llevar a producción con PostgreSQL, HTTPS y límite de intentos de inicio de sesión.
