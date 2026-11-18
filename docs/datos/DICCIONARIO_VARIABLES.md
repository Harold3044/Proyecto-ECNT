# Diccionario de variables

> Generado automáticamente con `python scripts/generar_diccionario.py` a partir de `src/ecnt_core/schemas.py`.
> Las mismas descripciones se muestran dentro de la plataforma (ambientes Administrador y EPS).

## Cómo leer los datos

- **Cada fila es un municipio** (no una persona). El proyecto trabaja con información territorial agregada.
- Los porcentajes del NBI son **porcentajes de personas** (0 a 100) que viven en hogares con esa carencia.
- Los indicadores NBI se publican para **tres áreas** del municipio, indicadas con un sufijo:

| Sufijo | Área | Significado |
|---|---|---|
| `_total` | Total municipal | Todo el municipio |
| `_cab` | Cabecera | Casco urbano |
| `_resto` | Centros poblados y rural disperso | Caseríos, corregimientos y viviendas aisladas en el campo (el DANE las publica juntas) |

  Ejemplo: `comp_servicios_resto = 45` significa que el 45 % de las personas que viven en la zona rural del municipio
  no tienen sanitario o no tienen acueducto (se abastecen de río, nacimiento, carrotanque o lluvia).
- **ECNT cardiometabólicas** = enfermedades hipertensivas, isquémicas del corazón (infarto), insuficiencia cardíaca,
  cerebrovasculares, otras circulatorias y diabetes (lista 6/67 de la OPS: 302, 303, 304, 306, 307, 309, 601).
- **Estandarizada por edad**: la tasa se calcula como si todos los municipios tuvieran la misma pirámide de edades
  (Colombia 2018), para comparar de forma justa municipios jóvenes y envejecidos.

## Relación con los determinantes sociales del proyecto

| Determinante | Variables |
|---|---|
| Agua potable y saneamiento básico | `comp_servicios_*` |
| Educación | `comp_inasistencia_*` (niños que no asisten) y `comp_dependencia_*` (baja escolaridad del jefe de hogar) |
| Condiciones socioeconómicas | `nbi_*`, `miseria_*`, `comp_vivienda_*`, `comp_hacinamiento_*`, `comp_dependencia_*` |
| Ruralidad / dispersión | `pct_poblacion_resto` y los indicadores con sufijo `_resto` |
| Estructura de edad | `pct_65_mas`, `pct_0_14` |

## 1. Dataset de modelado (`caribe_modelado.csv`, `externo_otras_regiones_modelado.csv`)

Una fila por municipio. Es el dataset con el que se entrenan y evalúan los modelos.

### Identificación

| Variable | Nombre | Unidad | Qué significa | Fuente |
|---|---|---|---|---|
| `divipola` | Código DIVIPOLA del municipio | — | Código oficial del DANE que identifica cada municipio de Colombia: 2 dígitos del departamento + 3 del municipio (p. ej. 20001 = Valledupar, Cesar). Es la llave que une todas las fuentes. Se guarda como texto para no perder el cero inicial (08001). | DANE |
| `cod_depto` | Código del departamento | — | Dos primeros dígitos del DIVIPOLA: 08 Atlántico, 13 Bolívar, 20 Cesar, 23 Córdoba, 44 La Guajira, 47 Magdalena, 70 Sucre, 88 San Andrés. | DANE |
| `departamento` | Departamento | — | Nombre del departamento al que pertenece el municipio. | DANE |
| `municipio` | Municipio | — | Nombre del municipio. Puede repetirse en distintos departamentos (p. ej. Villanueva); por eso la llave es el DIVIPOLA. | DANE |
| `periodo` | Periodo | — | Años que cubre la observación. '2018-2019' significa que la mortalidad se calculó sumando las defunciones y la población de esos dos años. | Calculada por el proyecto |
| `region` | Región | — | 'Caribe' para los municipios del estudio; 'Otras regiones' para los municipios del resto del país usados solo como datos independientes de validación externa. | Calculada por el proyecto |

### Demografía

| Variable | Nombre | Unidad | Qué significa | Fuente |
|---|---|---|---|---|
| `poblacion_2018` | Población total 2018 | personas | Número de habitantes del municipio en 2018. Indica el tamaño del territorio; en municipios pequeños las tasas son menos estables. | DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |
| `pct_poblacion_resto` | Población en zona rural (centros poblados y rural disperso) | % | Porcentaje de los habitantes que vive FUERA DE LA CABECERA municipal (centros poblados y zona rural dispersa). Es la medida de RURALIDAD / DISPERSIÓN del proyecto: 80 % significa que 8 de cada 10 personas viven en el campo o en caseríos. | Calculada por el proyecto con DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |
| `pct_65_mas` | Población de 65 años y más | % | Porcentaje de adultos mayores. Las ECNT aumentan mucho con la edad; esta variable describe el envejecimiento del municipio (la tasa objetivo ya está ajustada por edad). | Calculada por el proyecto con DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |
| `pct_0_14` | Población de 0 a 14 años | % | Porcentaje de niños y adolescentes. Un valor alto indica una población joven. | Calculada por el proyecto con DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |

### Resultado de salud

| Variable | Nombre | Unidad | Qué significa | Fuente |
|---|---|---|---|---|
| `def_ecnt_2018_2019` | Defunciones por ECNT 2018-2019 | defunciones | Número total de personas residentes en el municipio que murieron por ECNT cardiometabólicas en 2018 y 2019 (hipertensión, infarto e isquemia, insuficiencia cardíaca, accidente cerebrovascular, otras circulatorias y diabetes). Sirve para calcular la tasa; NO se usa como predictor. | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |
| `personas_anio_2018_2019` | Personas-año de exposición 2018-2019 | personas-año | Suma de la población de 2018 y la de 2019. Es el denominador de la tasa (cuántas personas estuvieron 'expuestas' durante los dos años). | Calculada por el proyecto con DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |
| `anios_con_registro` | Años con registro de defunciones | años | Cuántos de los años del periodo tienen información de defunciones para el municipio. Si falta algún año, la tasa no se calcula. | Calculada por el proyecto con DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |

### Variable objetivo

| Variable | Nombre | Unidad | Qué significa | Fuente |
|---|---|---|---|---|
| `tasa_mort_ecnt_std` | Mortalidad por ECNT estandarizada por edad (2018-2019) | por 100.000 hab. | VARIABLE QUE EL MODELO PREDICE. Muertes por ECNT cardiometabólicas por cada 100.000 habitantes, AJUSTADA POR EDAD: se calcula como si todos los municipios tuvieran la misma estructura de edades que Colombia en 2018, para que un municipio no salga 'peor' solo por tener más adultos mayores. Ejemplo: 170 = 170 muertes por cada 100.000 personas al año. Es mortalidad REGISTRADA: en zonas rurales dispersas puede haber subregistro. | Calculada por el proyecto con DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) y DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |

### Control

| Variable | Nombre | Unidad | Qué significa | Fuente |
|---|---|---|---|---|
| `es_sintetico` | ¿Dato sintético? | — | Verdadero si la fila fue generada artificialmente para pruebas (no es real). En los datasets oficiales del proyecto siempre es Falso. | Calculada por el proyecto |

### Determinantes sociales (NBI 2018)

| Variable | Nombre | Unidad | Qué significa | Fuente |
|---|---|---|---|---|
| `nbi_total` | Personas con NBI — total municipal | % | Porcentaje de personas que viven en hogares con AL MENOS UNA necesidad básica insatisfecha (vivienda inadecuada, servicios inadecuados, hacinamiento crítico, inasistencia escolar o alta dependencia económica). Es el indicador resumen de pobreza estructural del DANE: a mayor valor, más pobreza. Medido en todo el municipio (cabecera más zona rural). | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `miseria_total` | Personas en miseria — total municipal | % | Porcentaje de personas que viven en hogares con DOS O MÁS necesidades básicas insatisfechas al mismo tiempo. Mide la pobreza más severa. Medido en todo el municipio (cabecera más zona rural). | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `comp_vivienda_total` | Vivienda inadecuada — total municipal | % | Porcentaje de personas en viviendas con condiciones físicas impropias para habitar: piso de tierra, paredes de materiales precarios (tela, cartón, desechos) o sin paredes. Medido en todo el municipio (cabecera más zona rural). | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `comp_servicios_total` | Servicios inadecuados (agua y saneamiento) — total municipal | % | Porcentaje de personas en viviendas SIN SANITARIO o SIN ACUEDUCTO que se abastecen de agua de río, nacimiento, carrotanque o lluvia. Es el determinante de AGUA POTABLE y SANEAMIENTO BÁSICO del proyecto. Medido en todo el municipio (cabecera más zona rural). | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `comp_hacinamiento_total` | Hacinamiento crítico — total municipal | % | Porcentaje de personas en hogares donde duermen MÁS DE TRES PERSONAS POR CUARTO (sin contar cocina, baño ni garaje). Medido en todo el municipio (cabecera más zona rural). | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `comp_inasistencia_total` | Inasistencia escolar — total municipal | % | Porcentaje de personas en hogares con al menos un niño de 6 a 12 años que NO ASISTE a un centro educativo. Es uno de los determinantes de EDUCACIÓN del proyecto. Medido en todo el municipio (cabecera más zona rural). | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `comp_dependencia_total` | Alta dependencia económica — total municipal | % | Porcentaje de personas en hogares con MÁS DE TRES PERSONAS POR CADA OCUPADO y cuyo jefe de hogar tiene como máximo dos años de primaria aprobados. Combina ingreso (pocos ocupados) y EDUCACIÓN (baja escolaridad del jefe). Medido en todo el municipio (cabecera más zona rural). | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `nbi_cab` | Personas con NBI — cabecera | % | Porcentaje de personas que viven en hogares con AL MENOS UNA necesidad básica insatisfecha (vivienda inadecuada, servicios inadecuados, hacinamiento crítico, inasistencia escolar o alta dependencia económica). Es el indicador resumen de pobreza estructural del DANE: a mayor valor, más pobreza. Medido solo en la cabecera municipal (casco urbano). | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `miseria_cab` | Personas en miseria — cabecera | % | Porcentaje de personas que viven en hogares con DOS O MÁS necesidades básicas insatisfechas al mismo tiempo. Mide la pobreza más severa. Medido solo en la cabecera municipal (casco urbano). | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `comp_vivienda_cab` | Vivienda inadecuada — cabecera | % | Porcentaje de personas en viviendas con condiciones físicas impropias para habitar: piso de tierra, paredes de materiales precarios (tela, cartón, desechos) o sin paredes. Medido solo en la cabecera municipal (casco urbano). | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `comp_servicios_cab` | Servicios inadecuados (agua y saneamiento) — cabecera | % | Porcentaje de personas en viviendas SIN SANITARIO o SIN ACUEDUCTO que se abastecen de agua de río, nacimiento, carrotanque o lluvia. Es el determinante de AGUA POTABLE y SANEAMIENTO BÁSICO del proyecto. Medido solo en la cabecera municipal (casco urbano). | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `comp_hacinamiento_cab` | Hacinamiento crítico — cabecera | % | Porcentaje de personas en hogares donde duermen MÁS DE TRES PERSONAS POR CUARTO (sin contar cocina, baño ni garaje). Medido solo en la cabecera municipal (casco urbano). | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `comp_inasistencia_cab` | Inasistencia escolar — cabecera | % | Porcentaje de personas en hogares con al menos un niño de 6 a 12 años que NO ASISTE a un centro educativo. Es uno de los determinantes de EDUCACIÓN del proyecto. Medido solo en la cabecera municipal (casco urbano). | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `comp_dependencia_cab` | Alta dependencia económica — cabecera | % | Porcentaje de personas en hogares con MÁS DE TRES PERSONAS POR CADA OCUPADO y cuyo jefe de hogar tiene como máximo dos años de primaria aprobados. Combina ingreso (pocos ocupados) y EDUCACIÓN (baja escolaridad del jefe). Medido solo en la cabecera municipal (casco urbano). | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `nbi_resto` | Personas con NBI — centros poblados y rural disperso | % | Porcentaje de personas que viven en hogares con AL MENOS UNA necesidad básica insatisfecha (vivienda inadecuada, servicios inadecuados, hacinamiento crítico, inasistencia escolar o alta dependencia económica). Es el indicador resumen de pobreza estructural del DANE: a mayor valor, más pobreza. Medido solo fuera de la cabecera: centros poblados (caseríos, corregimientos) y zona rural dispersa (viviendas aisladas en el campo). El DANE publica estas dos zonas juntas. | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `miseria_resto` | Personas en miseria — centros poblados y rural disperso | % | Porcentaje de personas que viven en hogares con DOS O MÁS necesidades básicas insatisfechas al mismo tiempo. Mide la pobreza más severa. Medido solo fuera de la cabecera: centros poblados (caseríos, corregimientos) y zona rural dispersa (viviendas aisladas en el campo). El DANE publica estas dos zonas juntas. | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `comp_vivienda_resto` | Vivienda inadecuada — centros poblados y rural disperso | % | Porcentaje de personas en viviendas con condiciones físicas impropias para habitar: piso de tierra, paredes de materiales precarios (tela, cartón, desechos) o sin paredes. Medido solo fuera de la cabecera: centros poblados (caseríos, corregimientos) y zona rural dispersa (viviendas aisladas en el campo). El DANE publica estas dos zonas juntas. | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `comp_servicios_resto` | Servicios inadecuados (agua y saneamiento) — centros poblados y rural disperso | % | Porcentaje de personas en viviendas SIN SANITARIO o SIN ACUEDUCTO que se abastecen de agua de río, nacimiento, carrotanque o lluvia. Es el determinante de AGUA POTABLE y SANEAMIENTO BÁSICO del proyecto. Medido solo fuera de la cabecera: centros poblados (caseríos, corregimientos) y zona rural dispersa (viviendas aisladas en el campo). El DANE publica estas dos zonas juntas. | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `comp_hacinamiento_resto` | Hacinamiento crítico — centros poblados y rural disperso | % | Porcentaje de personas en hogares donde duermen MÁS DE TRES PERSONAS POR CUARTO (sin contar cocina, baño ni garaje). Medido solo fuera de la cabecera: centros poblados (caseríos, corregimientos) y zona rural dispersa (viviendas aisladas en el campo). El DANE publica estas dos zonas juntas. | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `comp_inasistencia_resto` | Inasistencia escolar — centros poblados y rural disperso | % | Porcentaje de personas en hogares con al menos un niño de 6 a 12 años que NO ASISTE a un centro educativo. Es uno de los determinantes de EDUCACIÓN del proyecto. Medido solo fuera de la cabecera: centros poblados (caseríos, corregimientos) y zona rural dispersa (viviendas aisladas en el campo). El DANE publica estas dos zonas juntas. | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |
| `comp_dependencia_resto` | Alta dependencia económica — centros poblados y rural disperso | % | Porcentaje de personas en hogares con MÁS DE TRES PERSONAS POR CADA OCUPADO y cuyo jefe de hogar tiene como máximo dos años de primaria aprobados. Combina ingreso (pocos ocupados) y EDUCACIÓN (baja escolaridad del jefe). Medido solo fuera de la cabecera: centros poblados (caseríos, corregimientos) y zona rural dispersa (viviendas aisladas en el campo). El DANE publica estas dos zonas juntas. | DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal |

## 2. Panel municipio-año (`caribe_panel_municipio_anio.csv`)

Una fila por municipio y año (2018-2021). Se usa para mostrar la evolución en el ambiente EPS.

### Identificación

| Variable | Nombre | Unidad | Qué significa | Fuente |
|---|---|---|---|---|
| `anio` | Año | — | Año calendario de la observación (2018-2021). | — |

### Demografía

| Variable | Nombre | Unidad | Qué significa | Fuente |
|---|---|---|---|---|
| `pob_total` | Población total del año | personas | Habitantes del municipio en ese año. | DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |
| `pob_cabecera` | Población en la cabecera | personas | Habitantes del casco urbano. | DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |
| `pob_resto` | Población en centros poblados y rural disperso | personas | Habitantes fuera de la cabecera (zona rural). | DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |
| `pob_0` | Población menores de 1 año | personas | Habitantes menores de 1 año. Se usa para ajustar la tasa por edad. | DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |
| `pob_1-4` | Población de 1 a 4 años | personas | Habitantes de 1 a 4 años. Se usa para ajustar la tasa por edad. | DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |
| `pob_5-14` | Población de 5 a 14 años | personas | Habitantes de 5 a 14 años. Se usa para ajustar la tasa por edad. | DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |
| `pob_15-44` | Población de 15 a 44 años | personas | Habitantes de 15 a 44 años. Se usa para ajustar la tasa por edad. | DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |
| `pob_45-64` | Población de 45 a 64 años | personas | Habitantes de 45 a 64 años. Se usa para ajustar la tasa por edad. | DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |
| `pob_65-84` | Población de 65 a 84 años | personas | Habitantes de 65 a 84 años. Se usa para ajustar la tasa por edad. | DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |
| `pob_85-99` | Población de 85 a 99 años | personas | Habitantes de 85 a 99 años. Se usa para ajustar la tasa por edad. | DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |
| `pob_100+` | Población de 100 años y más | personas | Habitantes de 100 años y más. Se usa para ajustar la tasa por edad. | DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042 |

### Resultado de salud

| Variable | Nombre | Unidad | Qué significa | Fuente |
|---|---|---|---|---|
| `def_todas_causas` | Defunciones por todas las causas | defunciones | Total de muertes de residentes del municipio en el año, por cualquier causa. | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |
| `def_ecnt` | Defunciones por ECNT cardiometabólicas | defunciones | Muertes por hipertensión, enfermedad isquémica, insuficiencia cardíaca, enfermedad cerebrovascular, otras circulatorias y diabetes en el año. | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |
| `def_hta` | Defunciones por enfermedades hipertensivas | defunciones | Muertes por hipertensión arterial (código 302). | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |
| `def_isquemica` | Defunciones por enfermedad isquémica del corazón | defunciones | Infartos y otras isquemias (código 303). | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |
| `def_cerebrovascular` | Defunciones por enfermedad cerebrovascular | defunciones | Accidentes cerebrovasculares o 'derrames' (código 307). | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |
| `def_diabetes` | Defunciones por diabetes | defunciones | Muertes por diabetes mellitus (código 601). | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |
| `tasa_ecnt_cruda` | Mortalidad por ECNT cruda | por 100.000 hab. | Muertes por ECNT por cada 100.000 habitantes SIN ajustar por edad. Municipios con más adultos mayores tienden a tener tasas crudas más altas. | Calculada por el proyecto |
| `tasa_ecnt_std` | Mortalidad por ECNT estandarizada por edad (anual) | por 100.000 hab. | Igual que la variable objetivo, pero para un solo año. Permite comparar municipios y años sin el efecto de la estructura de edades. | Calculada por el proyecto |
| `def_0` | Defunciones por ECNT menores de 1 año | defunciones | Muertes por ECNT de personas menores de 1 año. Se usa para ajustar la tasa por edad. | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |
| `def_1-4` | Defunciones por ECNT de 1 a 4 años | defunciones | Muertes por ECNT de personas de 1 a 4 años. Se usa para ajustar la tasa por edad. | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |
| `def_5-14` | Defunciones por ECNT de 5 a 14 años | defunciones | Muertes por ECNT de personas de 5 a 14 años. Se usa para ajustar la tasa por edad. | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |
| `def_15-44` | Defunciones por ECNT de 15 a 44 años | defunciones | Muertes por ECNT de personas de 15 a 44 años. Se usa para ajustar la tasa por edad. | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |
| `def_45-64` | Defunciones por ECNT de 45 a 64 años | defunciones | Muertes por ECNT de personas de 45 a 64 años. Se usa para ajustar la tasa por edad. | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |
| `def_65-84` | Defunciones por ECNT de 65 a 84 años | defunciones | Muertes por ECNT de personas de 65 a 84 años. Se usa para ajustar la tasa por edad. | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |
| `def_85-99` | Defunciones por ECNT de 85 a 99 años | defunciones | Muertes por ECNT de personas de 85 a 99 años. Se usa para ajustar la tasa por edad. | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |
| `def_100+` | Defunciones por ECNT de 100 años y más | defunciones | Muertes por ECNT de personas de 100 años y más. Se usa para ajustar la tasa por edad. | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |
| `def_desconocida` | Defunciones por ECNT con edad desconocida | defunciones | Muertes por ECNT de personas con edad desconocida. Se usa para ajustar la tasa por edad. | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |

### Control

| Variable | Nombre | Unidad | Qué significa | Fuente |
|---|---|---|---|---|
| `registro_defunciones` | ¿Hay registro de defunciones? | — | Verdadero si el DANE publicó defunciones para el municipio ese año. | DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas) |
| `periodo_pandemia` | ¿Año de pandemia? | — | Verdadero para 2020 y 2021: la COVID-19 alteró la mortalidad y su registro; por eso esos años no se usan en la variable objetivo. | Calculada por el proyecto |

## 3. Resultados del modelo (ambiente EPS e informes)

### Resultado del modelo

| Variable | Nombre | Unidad | Qué significa | Fuente |
|---|---|---|---|---|
| `predicho` | Mortalidad esperada por el modelo | por 100.000 hab. | Mortalidad por ECNT que el modelo estima según los determinantes sociales y demográficos del municipio. Para municipios usados en el entrenamiento se calcula 'fuera de muestra' (sin que el modelo haya visto ese municipio). | — |
| `observado` | Mortalidad registrada | por 100.000 hab. | Mortalidad realmente registrada por el DANE (la variable objetivo). | — |
| `lim_inf` | Límite inferior del intervalo del 90 % | por 100.000 hab. | Con 90 % de confianza, la mortalidad esperada no es menor a este valor. Si lo registrado queda por debajo, puede haber subregistro. | — |
| `lim_sup` | Límite superior del intervalo del 90 % | por 100.000 hab. | Con 90 % de confianza, la mortalidad esperada no supera este valor. Si lo registrado queda por encima, hay un exceso que amerita revisión. | — |
| `nivel` | Nivel de mortalidad esperada | — | Quintil del municipio dentro del Caribe según la mortalidad esperada: 'muy bajo' es el 20 % de municipios con valores más bajos y 'muy alto' el 20 % con valores más altos. | — |
| `poblacion` | Población 2018 | personas | Habitantes del municipio en 2018. | — |
