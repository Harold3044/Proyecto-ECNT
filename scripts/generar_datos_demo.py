"""Genera los archivos de DEMOSTRACIÓN para mostrar la plataforma en vivo.

Todos los valores provienen de los datasets REALES procesados (DANE). Para poder mostrar la
limpieza, al archivo 1 se le introducen A PROPÓSITO problemas de calidad documentados:
3 filas duplicadas y 4 celdas vacías. Ningún valor se inventa ni se modifica.

Uso:  python scripts/generar_datos_demo.py      (requiere scripts/construir_dataset_caribe.py)
Salida: data/demo/
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ecnt_core.config import DATA, PROCESSED

OUT = DATA / "demo"
DUPLICADOS = ["20001", "13001", "44847"]  # Valledupar, Cartagena, Uribia
VACIOS = [("23001", "nbi_resto"), ("47001", "nbi_resto"), ("70001", "comp_servicios_cab"),
          ("08001", "comp_servicios_cab")]  # Montería, Santa Marta, Sincelejo, Barranquilla


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    dtype = {"divipola": str, "cod_depto": str}
    caribe = pd.read_csv(PROCESSED / "caribe_modelado.csv", dtype=dtype)
    externo = pd.read_csv(PROCESSED / "externo_otras_regiones_modelado.csv", dtype=dtype)

    # 1) Dataset principal para la carga masiva (Caribe, real) con problemas de calidad introducidos
    demo = caribe.copy()
    for div, col in VACIOS:
        demo.loc[demo.divipola == div, col] = np.nan
    dup = demo[demo.divipola.isin(DUPLICADOS)]
    demo = pd.concat([demo, dup], ignore_index=True)
    demo.to_csv(OUT / "DEMO_1_caribe_para_cargar.csv", index=False, encoding="utf-8")

    # 2) Datos nuevos para el módulo de predicción: 40 municipios reales de otras regiones, completos
    nuevos = (externo.dropna().sort_values(["departamento", "municipio"])
              .groupby("departamento", group_keys=False).head(2).head(40))
    nuevos.to_excel(OUT / "DEMO_2_datos_nuevos_otras_regiones.xlsx", index=False)

    print(f"DEMO_1: {len(demo)} filas ({len(caribe)} municipios + {len(dup)} duplicados), "
          f"{int(demo.isna().sum().sum())} celdas vacías")
    print(f"DEMO_2: {len(nuevos)} municipios de {nuevos.departamento.nunique()} departamentos")


if __name__ == "__main__":
    main()
