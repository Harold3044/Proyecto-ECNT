"""Construye los datasets territoriales REALES de la región Caribe a partir de fuentes DANE.

Entradas (ver docs/datos/):
  data/raw/CNPV-2018-NBI-DIVIPOLA-2021.xlsx
  data/raw/dane_proyecciones/PPED-AreaSexoEdadMun-2018-2042_VP.xlsx
  data/raw/dane_eevv/EEVV_C5_{2018..2021}_def.xls

Salidas:
  data/processed/caribe_panel_municipio_anio.csv   municipio × año (2018-2021): defunciones, población, tasas
  data/processed/caribe_modelado.csv               municipio (corte transversal) para modelado
  data/processed/manifiesto.json                   hashes de entradas/salidas y parámetros

Uso:  python scripts/construir_dataset_caribe.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import msoffcrypto
import numpy as np
import pandas as pd

from ecnt_core.config import AGE_LABELS, CARIBE_DEPTOS, ECNT_CAUSES, INTERIM, PROCESSED, RAW
from ecnt_core.sources import dane

NBI_FILE = RAW / "CNPV-2018-NBI-DIVIPOLA-2021.xlsx"
POP_FILE = RAW / "dane_proyecciones" / "PPED-AreaSexoEdadMun-2018-2042_VP.xlsx"
EEVV_DIR = RAW / "dane_eevv"
YEARS = [2018, 2019, 2020, 2021]
TARGET_YEARS = [2018, 2019]  # años prepandemia agregados para la variable objetivo
DEPTOS = list(CARIBE_DEPTOS)
SUBGRUPOS = {"hta": ["302"], "isquemica": ["303"], "cerebrovascular": ["307"], "diabetes": ["601"]}


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decrypt_if_needed(year: int):
    """Los cuadros 2019+ vienen con la protección estándar de Excel (clave pública VelvetSweatshop)."""
    src = EEVV_DIR / f"EEVV_C5_{year}_def.xls"
    if year == 2018:
        return src
    dst = INTERIM / "eevv_decrypted" / src.name
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(src, "rb") as f, open(dst, "wb") as g:
            office = msoffcrypto.OfficeFile(f)
            office.load_key(password="VelvetSweatshop")
            office.decrypt(g)
    return dst


def load_deaths() -> pd.DataFrame:
    frames = [dane.read_deaths_cuadro5_2018(decrypt_if_needed(2018), DEPTOS)]
    for y in YEARS[1:]:
        frames.append(dane.read_deaths_cuadro5_unificado(decrypt_if_needed(y), y, DEPTOS))
    return pd.concat(frames, ignore_index=True)


def aggregate_deaths(deaths: pd.DataFrame) -> pd.DataFrame:
    """Por municipio-año: defunciones ECNT por edad, total de defunciones y subgrupos."""
    age_cols = [f"def_{g}" for g in [*AGE_LABELS, "desconocida"]]
    deaths = deaths.assign(n=deaths[age_cols].sum(axis=1))
    key = ["divipola", "anio"]
    ecnt = deaths[deaths["causa"].isin(ECNT_CAUSES)].groupby(key)[age_cols].sum()
    total = deaths[deaths["causa"] == "TOTAL"].groupby(key)["n"].sum().rename("def_todas_causas")
    out = total.to_frame().join(ecnt, how="left")
    out[age_cols] = out[age_cols].fillna(0).astype(int)  # municipio con registro pero sin muertes ECNT
    out["def_ecnt"] = out[age_cols].sum(axis=1)
    for name, codes in SUBGRUPOS.items():
        s = deaths[deaths["causa"].isin(codes)].groupby(key)["n"].sum()
        out[f"def_{name}"] = s.reindex(out.index).fillna(0).astype(int)
    return out.reset_index()


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    print("1/5 NBI…")
    nbi = dane.read_nbi(NBI_FILE)
    nbi = nbi[nbi["cod_depto"].isin(DEPTOS)].copy()

    print("2/5 Población (archivo grande, ~1 min)…")
    all_deptos = sorted({f"{i:02d}" for i in range(5, 100)})
    pop_all = dane.read_population(POP_FILE, all_deptos, YEARS)
    pop_col = pop_all[(pop_all.anio == 2018) & (pop_all.area == "total")]
    std = pop_col[[f"pob_{g}" for g in AGE_LABELS]].sum()
    std_weights = pd.Series(std.values / std.sum(), index=AGE_LABELS)  # estándar: Colombia 2018
    pop = pop_all[pop_all["divipola"].str[:2].isin(DEPTOS)]
    pop_tot = pop[pop.area == "total"].drop(columns="area")
    pop_area = pop.pivot_table(index=["divipola", "anio"], columns="area", values="pob_total", aggfunc="sum")
    pop_area = pop_area.rename(columns={"cab": "pob_cabecera", "resto": "pob_resto"})[
        ["pob_cabecera", "pob_resto"]
    ]

    print("3/5 Defunciones 2018-2021…")
    deaths = aggregate_deaths(load_deaths())

    print("4/5 Panel municipio-año…")
    panel = pop_tot.merge(pop_area.reset_index(), on=["divipola", "anio"], how="left")
    panel = panel.merge(deaths, on=["divipola", "anio"], how="left")
    panel["registro_defunciones"] = panel["def_todas_causas"].notna()
    panel["tasa_ecnt_cruda"] = panel["def_ecnt"] / panel["pob_total"] * 1e5
    panel["tasa_ecnt_std"] = dane.age_standardized_rate(
        panel[[f"def_{g}" for g in [*AGE_LABELS, "desconocida"]]].fillna(0),
        panel[[f"pob_{g}" for g in AGE_LABELS]],
        std_weights,
    ).where(panel["registro_defunciones"])
    panel["periodo_pandemia"] = panel["anio"] >= 2020
    panel = panel.merge(nbi[["divipola", "departamento", "municipio"]], on="divipola", how="left")
    panel["es_sintetico"] = False
    panel.to_csv(PROCESSED / "caribe_panel_municipio_anio.csv", index=False)

    print("5/5 Dataset de modelado…")
    p = panel[panel.anio.isin(TARGET_YEARS)]
    agg_cols = [f"def_{g}" for g in [*AGE_LABELS, "desconocida"]] + [f"pob_{g}" for g in AGE_LABELS]
    agg = p.groupby("divipola")[agg_cols + ["def_ecnt", "pob_total"]].sum(min_count=1)
    agg["anios_con_registro"] = p.groupby("divipola")["registro_defunciones"].sum()
    agg["tasa_ecnt_std"] = dane.age_standardized_rate(
        agg[[f"def_{g}" for g in [*AGE_LABELS, "desconocida"]]], agg[[f"pob_{g}" for g in AGE_LABELS]],
        std_weights,
    )
    agg.loc[agg["anios_con_registro"] < len(TARGET_YEARS), "tasa_ecnt_std"] = np.nan

    p18 = panel[panel.anio == 2018].set_index("divipola")
    demo = pd.DataFrame(
        {
            "poblacion_2018": p18["pob_total"],
            "pct_poblacion_resto": p18["pob_resto"] / p18["pob_total"] * 100,
            "pct_65_mas": (p18["pob_65-84"] + p18["pob_85-99"] + p18["pob_100+"]) / p18["pob_total"] * 100,
            "pct_0_14": (p18["pob_0"] + p18["pob_1-4"] + p18["pob_5-14"]) / p18["pob_total"] * 100,
        }
    )
    model = (
        nbi.set_index("divipola")
        .join(demo)
        .join(agg[["def_ecnt", "pob_total", "anios_con_registro", "tasa_ecnt_std"]]
              .rename(columns={"def_ecnt": "def_ecnt_2018_2019", "pob_total": "personas_anio_2018_2019",
                               "tasa_ecnt_std": "tasa_mort_ecnt_std"}))
        .reset_index()
    )
    model.insert(4, "periodo", "2018-2019")
    model["es_sintetico"] = False
    model.to_csv(PROCESSED / "caribe_modelado.csv", index=False)

    manifest = {
        "generado": datetime.now(UTC).isoformat(timespec="seconds"),
        "variable_objetivo": "tasa_mort_ecnt_std: defunciones por ECNT cardiometabólicas (lista 6/67 OPS: "
        + ", ".join(ECNT_CAUSES) + ") por 100.000 hab., estandarizada por edad (método directo, "
        "estándar = población de Colombia 2018), municipio de residencia, agregado 2018-2019",
        "entradas": {str(f.relative_to(RAW)): sha256(f) for f in
                     [NBI_FILE, POP_FILE, *[EEVV_DIR / f"EEVV_C5_{y}_def.xls" for y in YEARS]]},
        "salidas": {
            "caribe_panel_municipio_anio.csv": {"filas": len(panel)},
            "caribe_modelado.csv": {
                "filas": len(model),
                "objetivo_no_nulo": int(model.tasa_mort_ecnt_std.notna().sum()),
            },
        },
        "pesos_estandar": std_weights.round(6).to_dict(),
    }
    (PROCESSED / "manifiesto.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), "utf-8")
    print(json.dumps(manifest["salidas"], indent=2))


if __name__ == "__main__":
    main()
