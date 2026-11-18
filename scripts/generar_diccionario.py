"""Genera docs/datos/DICCIONARIO_VARIABLES.md desde ecnt_core.schemas (fuente única de las descripciones).

Uso:  python scripts/generar_diccionario.py
"""

from __future__ import annotations

from ecnt_core.config import ROOT
from ecnt_core.schemas import CANONICAL, OUTPUTS, PANEL, VariableSpec

OUT = ROOT / "docs" / "datos" / "DICCIONARIO_VARIABLES.md"

INTRO = """# Diccionario de variables

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
"""


def table(specs: list[VariableSpec]) -> str:
    rows = ["| Variable | Nombre | Unidad | Qué significa | Fuente |", "|---|---|---|---|---|"]
    for s in specs:
        exp = s.explicacion.replace("|", "/").replace("\n", " ")
        rows.append(f"| `{s.name}` | {s.description} | {s.unit or '—'} | {exp} | {s.fuente or '—'} |")
    return "\n".join(rows)


def by_group(specs: dict[str, VariableSpec]) -> str:
    groups: dict[str, list[VariableSpec]] = {}
    for s in specs.values():
        groups.setdefault(s.grupo or "Otras", []).append(s)
    return "\n\n".join(f"### {g}\n\n{table(v)}" for g, v in groups.items())


def main() -> None:
    text = "\n".join([
        INTRO,
        "## 1. Dataset de modelado (`caribe_modelado.csv`, `externo_otras_regiones_modelado.csv`)\n",
        "Una fila por municipio. Es el dataset con el que se entrenan y evalúan los modelos.\n",
        by_group(CANONICAL),
        "\n## 2. Panel municipio-año (`caribe_panel_municipio_anio.csv`)\n",
        "Una fila por municipio y año (2018-2021). Se usa para mostrar la evolución en el ambiente EPS.\n",
        by_group(PANEL),
        "\n## 3. Resultados del modelo (ambiente EPS e informes)\n",
        by_group(OUTPUTS),
        "",
    ])
    OUT.write_text(text, encoding="utf-8")
    print(f"Escrito {OUT} ({len(CANONICAL) + len(PANEL) + len(OUTPUTS)} variables)")


if __name__ == "__main__":
    main()
