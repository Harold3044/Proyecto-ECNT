# Ficha de fuente — NBI CNPV 2018 (DANE)

| Campo | Valor |
|---|---|
| Entidad | DANE — Censo Nacional de Población y Vivienda 2018 |
| Archivo | `data/raw/CNPV-2018-NBI-DIVIPOLA-2021.xlsx` (hoja `Municipios`) |
| SHA‑256 | `32c63625b8dce33bfe4bc15dd21d5aceda2b10a01295b20a91b5995f213a755f` |
| Obtención | Página DANE "Necesidades Básicas Insatisfechas (NBI)" → anexo municipal CNPV 2018, codificación DIVIPOLA 2021 |
| Cobertura | Todos los municipios de Colombia (filas desde la 11 de la hoja); este proyecto filtra los 8 departamentos de la región Caribe |
| Temporalidad | Un solo corte: 2018 |
| Unidad | Municipio × área (**Total**, **Cabeceras**, **Centros poblados y rural disperso**) |
| Llave | `Código Departamento` (2 dígitos) + `Código Municipio` (3 dígitos) = DIVIPOLA de 5 dígitos (texto) |

## Variables (porcentaje de personas, 0–100) — se repiten para cada área

| Columna original | Nombre canónico |
|---|---|
| Prop de Personas en NBI (%) | `nbi` |
| Prop de Personas en miseria | `miseria` |
| Componente vivienda | `comp_vivienda` |
| Componente Servicios (agua y saneamiento) | `comp_servicios` |
| Componente Hacinamiento | `comp_hacinamiento` |
| Componente Inasistencia (niños 6–12 que no asisten) | `comp_inasistencia` |
| Componente dependencia económica (incluye baja escolaridad del jefe) | `comp_dependencia` |

Sufijos canónicos: `_total`, `_cab` (cabeceras), `_resto` (centros poblados y rural disperso).

## Limitaciones
- **No separa el rural disperso puro**: lo agrupa con los centros poblados.
- Corte único (2018): no hay variación temporal de los determinantes.
- Algunos municipios no tienen población en "resto" y aparecen con valores vacíos o cero en esa área (se trata en Fase 3).
- El NBI es un índice de carencias del hogar; el agua y el saneamiento aparecen dentro del componente "servicios", no como coberturas por separado.
