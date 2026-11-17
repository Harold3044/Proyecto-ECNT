# Inventario inicial (Fase 0) — 2026-11-17

Inspección **de solo lectura**. No se movió, copió, modificó ni eliminó ningún archivo.

## 1. Directorio del proyecto

| Ruta | Estado |
|---|---|
| `Proyecto-ECNT/` | Vacío al iniciar la Fase 0. No es repositorio Git. |
| Repositorio remoto mencionado | `https://github.com/LuisSantiago09/riesgo-ecnt.git` (en `../repositoriogithub.txt`). No se consultó. |

## 2. Herramientas instaladas en el equipo

| Herramienta | Versión | Observación |
|---|---|---|
| Python | 3.13.13 | El intérprete global **no** tiene pandas/scikit-learn. |
| Node.js / npm | 26.2.0 / 11.13.0 | Suficiente para una app React/Vite. |
| Docker | 29.2.1 | Instalado (no se verificó que el daemon esté corriendo). |
| Git | 2.53.0 | Disponible. |
| PostgreSQL (psql) | No instalado | Se propone usarlo vía Docker. |

## 3. Material previo encontrado en la carpeta padre (`../`)

### 3.1 Datos reales (fuente oficial)

| Archivo | Contenido | Utilidad |
|---|---|---|
| `CNPV-2018-NBI-DIVIPOLA-2021.xlsx` | NBI CNPV 2018 por municipio (1.122 municipios), desagregado en **Total / Cabeceras / Centros poblados y rural disperso**: NBI, miseria, componentes vivienda, servicios, hacinamiento, inasistencia, dependencia económica. | Fuente principal de predictores. Ojo: DANE agrupa *centros poblados + rural disperso* en una sola columna. |
| `20_Cesar/…/CNPV2018_{1VIV,2HOG,3FALL,5PER,MGN}_A2_20.CSV` | Microdatos del Censo 2018, **solo departamento del Cesar** (vivienda, hogar, fallecidos, personas, marco geográfico). Incluye `UA_CLASE` (1 cabecera, 2 centro poblado, 3 rural disperso). | Única fuente local que separa **rural disperso puro**. Cobertura: 25 municipios. |
| `CNPV2018_DIC_ANDA2_MGN_MZA_20200129.zip` | Diccionario de datos del CNPV 2018. | Documentación de variables. |
| `ano-corrido-CUADRO5-NOFETALES-2018-PRELIMINAR.xls` | DANE Estadísticas Vitales — defunciones no fetales 2018 (preliminar). No se pudo abrir (requiere `python-calamine`/`xlrd`). | Posible base para una **variable objetivo alternativa** (mortalidad por ECNT). Revisar en Fase 2. |

### 3.2 Datos derivados por el equipo

| Archivo | Contenido | Estado de los datos |
|---|---|---|
| `Caribe_Agua_Saneamiento_Educacion.xlsx` | 7 hojas: NBI de 197 municipios del Caribe, microdatos Cesar por municipio × clase, departamentos, diccionario. | Real (derivado de DANE). |
| `Fase 2/Dataset_ECNT_Social_Salud_2316_registros.xlsx` | 193 municipios × 12 años (2012–2023). | **Población, casos y prevalencias SIMULADOS** (lo declara el propio archivo: `estado_datos_salud = "SIMULADO - NO OFICIAL"`). Los indicadores sociales son de 2018 **repetidos** en los 12 años; 7 variables con 87 % de nulos. |
| `files/fase2-ecnt-caribe/` | Proyecto Python previo (paquete `src/ecnt`, scripts 01–03, tests, modelos `.joblib`, figuras, métricas). | Objetivo `ir_ecnt_sim` **simulado** con `target_simulation.py`. Tiene `.venv` propio con pandas/sklearn. |

### 3.3 Documentos

`PROPUESTA DE PROYECTO DE AULA 2.pdf` (Fases 1 y 2, 25 págs.), `Documento_Tecnico_Fase2.docx`, `Predicción del Riesgo de ECNT en Población Dispersa.pdf`, `Fases_Proyecto_Aula_IA.pdf`, `EstadoDelArte.pdf`, notebooks de EDA (`EDA_Caribe_…ipynb`, `Fase 2/riesgo_ecnt.ipynb`, `Filtrando data set`).

## 4. Conclusiones del inventario

1. **No existe ninguna variable objetivo de salud real** en el material disponible. Todo resultado de modelado previo mide la recuperación de una señal simulada.
2. El dataset de 2.316 registros **no debe reutilizarse como base**: su estructura longitudinal es artificial (predictores constantes en el tiempo, población simulada).
3. El código previo (`src/ecnt`) contiene piezas reutilizables (pipelines de sklearn, partición por municipio, pruebas de no‑fuga), pero su configuración está acoplada al objetivo simulado.
4. Los predictores reales disponibles son **transversales (2018)**. No hay aún variación temporal de los determinantes.
