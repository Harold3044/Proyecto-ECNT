# Ficha de fuente — Proyecciones de población municipal por área, sexo y edad (DANE)

| Campo | Valor |
|---|---|
| Entidad | DANE — Proyecciones de población con base en el CNPV 2018 (actualización post‑COVID) |
| Archivo | `data/raw/dane_proyecciones/PPED-AreaSexoEdadMun-2018-2042_VP.xlsx` (131 MB) |
| URL | `https://www.dane.gov.co/files/censo2018/proyecciones-de-poblacion/Municipal/PPED-AreaSexoEdadMun-2018-2042_VP.xlsx` |
| Hoja | `PobMunicipalxÁreaSexoEdad` (tercera hoja) |
| Cobertura | Todos los municipios, 2018–2042 |
| Áreas | `Cabecera Municipal`, `Centros Poblados y Rural Disperso`, `Total` |
| Edades | Simples de 0 a 100 y más, por sexo y total |

## Uso en el proyecto
- **Denominador** de las tasas de mortalidad (población total del municipio, año a año).
- **Población estándar** para la estandarización por edad: Colombia 2018 (suma de todos los municipios), agregada en los grupos de edad del Cuadro 5.
- Predictores demográficos: `pct_poblacion_resto` (proxy de ruralidad), `pct_65_mas`, `pct_0_14`, `poblacion_2018`.

## Limitaciones
- **No separa el rural disperso puro**: lo agrupa con los centros poblados. Confirma la observación C‑2.
- Son proyecciones (modelo demográfico), no conteos.
