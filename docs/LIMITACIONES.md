# Limitaciones del proyecto

Este documento debe leerse junto con cualquier resultado de la plataforma.

## 1. Metodológicas (de los datos y la variable objetivo)

1. **Mide mortalidad registrada, no prevalencia ni riesgo individual.** La variable objetivo es la mortalidad por ECNT cardiometabólicas estandarizada por edad (DANE, 2018–2019). La fórmula original (personas únicas con ECNT en RIPS / población rural dispersa) no pudo construirse: los RIPS con identificación de personas no son públicos y no distinguen el rural disperso.
2. **No se aísla el rural disperso puro.** El NBI y las proyecciones del DANE agrupan *centros poblados y rural disperso* ("resto"). La dimensión de dispersión entra por los predictores (NBI del área resto, % de población resto). Los microdatos censales con rural disperso puro solo estaban disponibles para el Cesar (25 de 197 municipios).
3. **Subregistro.** La relación observada es inversa (más ruralidad → menos mortalidad *registrada*, ρ = −0,37). Es coherente con subregistro y baja certificación médica en zonas dispersas (p. ej. Uribia y Manaure). Por eso la plataforma marca "posible subregistro" en lugar de "bajo riesgo".
4. **Diseño transversal.** Los determinantes son de un único corte (Censo 2018). No hay variación temporal de los predictores, así que no se modela dinámica temporal ni se pronostica a futuro con nuevos determinantes. La evolución 2018–2021 que ve la EPS es la mortalidad registrada (2020–2021 afectada por la pandemia).
5. **Muestra pequeña** (197 municipios; 40 de prueba). Las métricas tienen intervalos amplios: R² de prueba 0,30–0,33 con IC 95 % aproximado de −0,01 a 0,52.
6. **Capacidad predictiva modesta.** Los determinantes disponibles explican ≈ 20–30 % de la variación entre municipios; el modelo mejora ≈ 14 % sobre la línea base. En la validación externa (917 municipios de otras regiones) apenas transfiere (R² 0,08).
7. **Conteos pequeños.** 18 municipios tienen menos de 20 defunciones por ECNT en dos años: sus tasas son inestables.
8. **Asociación, no causalidad**, y riesgo de **falacia ecológica**: los resultados describen territorios, no personas.
9. **ENSIN no se integró**: solo es representativa a nivel regional/departamental.

## 2. Técnicas

1. **SQLite** como base de datos por defecto. Es adecuada para un solo servidor y bajo volumen. En Docker sobre Windows, la carpeta montada hace la API unas 4 veces más lenta: para producción use PostgreSQL o un volumen nombrado.
2. El entrenamiento es **síncrono**: comparar 5 modelos con ajuste de hiperparámetros tarda unos 45 s.
3. El mapa usa **puntos** en la cabecera municipal, no polígonos municipales.
4. Las interfaces son Streamlit (no React): funcionales, pero con personalización visual limitada.
5. Los informes se exportan en **CSV**, no en PDF.
6. No hay HTTPS, límite de intentos de inicio de sesión ni cambio obligatorio de contraseña (ver `SEGURIDAD.md`).
7. Las pruebas de interfaz son automáticas (`AppTest`). No reemplazan una revisión de usabilidad con usuarios reales.

## 3. De uso

- **No** debe usarse para diagnóstico, tamizaje individual ni decisiones clínicas.
- Las alertas son insumos para **priorizar la revisión** y requieren validación humana con información epidemiológica local.
- Los territorios rurales dispersos no deben etiquetarse como de "bajo riesgo" a partir de la mortalidad registrada.
