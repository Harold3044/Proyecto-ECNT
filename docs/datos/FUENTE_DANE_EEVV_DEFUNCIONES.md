# Ficha de fuente — Estadísticas Vitales: defunciones no fetales, Cuadro 5 (DANE)

| Campo | Valor |
|---|---|
| Entidad | DANE — Estadísticas Vitales (EEVV) |
| Cuadro | Cuadro 5: *Defunciones por grupos de edad y sexo, según departamento y municipio de residencia y grupos de causas de defunción (lista de causas agrupadas 6/67 CIE‑10 de OPS)* |
| Años usados | 2018, 2019, 2020, 2021 (**cifras definitivas**) |
| Página | dane.gov.co → Estadísticas por tema → Salud → Nacimientos y defunciones → Defunciones no fetales → año |
| Unidad | Municipio de **residencia** × causa (6/67) × grupo de edad × sexo |
| Grupos de edad | <1, 1–4, 5–14, 15–44, 45–64, 65–84, 85–99, 100+, desconocida |

## Archivos (en `data/raw/dane_eevv/`)

| Archivo local | URL de origen (relativa a `https://www.dane.gov.co/files/investigaciones/poblacion/`) |
|---|---|
| `EEVV_C5_2018_def.xls` | `2019/20-diciembre-2019/nofetales2018p/CUADRO5-NOFETALES-2018-def.xls` |
| `EEVV_C5_2019_def.xls` | `2020/23-diciembre-2020/defunciones-no-fetales-2019-cuadro-definitivo-2019.xls` |
| `EEVV_C5_2020_def.xls` | `2022/25-marzo-2022/defunciones-no-fetales2020-cuadros-unificados-definitivo-2020.xls` |
| `EEVV_C5_2021_def.xls` | `2022/22-diciembre-2022/defunciones-no-fetales2021-cuadro-definitivo-2021.xls` |

Hashes SHA‑256 en `data/processed/manifiesto.json`.

## Particularidades técnicas verificadas
- 2018: una hoja por departamento, municipio en una fila de cabecera (`"20001 Valledupar"`).
- 2019–2021: hoja `Cuadro5` única con código DIVIPOLA numérico; los archivos tienen la **protección estándar de Excel de solo lectura** (clave pública `VelvetSweatshop`). Se desprotegen en `data/interim/` sin alterar el original. No es una restricción de acceso: los datos son públicos.
- La fila de total por municipio aparece como `TOTAL` (2018–2020) o `Total` (2021).
- **Validación**: la suma de defunciones municipales coincide exactamente con el total departamental publicado (ej. Cesar: 4.910 / 4.966 / 6.258 / 7.536 en 2018–2021). Prueba automática en `tests/test_sources_dane.py`.

## Limitaciones
- **No desagrega por área de residencia** (cabecera / centro poblado / rural disperso). Esa variable sí existe en los microdatos EEVV (`AREA_RES`), cuya integración queda como trabajo futuro.
- Mide **mortalidad**, no prevalencia.
- Posible **subregistro** de defunciones y de causa en zonas rurales dispersas y en territorios indígenas (ver hallazgo H‑1 en `ESTRATEGIA_DATOS.md`).
- 2020–2021: efecto de la pandemia (competencia de causas, cambios en la certificación). No se usan en la variable objetivo principal.
