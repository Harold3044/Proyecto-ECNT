"""Carga los datasets REALES procesados en la plataforma y entrena la comparación de modelos.

Uso:
  python scripts/cargar_datos_iniciales.py                       # carga datos + compara modelos
  python scripts/cargar_datos_iniciales.py --aprobar-y-publicar  # además aprueba y publica el modelo elegido

La aprobación/publicación es una decisión humana: el indicador ``--aprobar-y-publicar`` debe
usarlo conscientemente el administrador; queda registrado en la auditoría con su justificación.
Requiere haber ejecutado antes scripts/construir_dataset_caribe.py.
"""

from __future__ import annotations

import argparse

from sqlalchemy import select

from ecnt_api.config import get_settings
from ecnt_api.db import Base, make_engine, make_sessionmaker
from ecnt_api.main import bootstrap
from ecnt_api.orm import Dataset, Usuario, VersionModelo
from ecnt_api.services import alerts, datasets, modeling
from ecnt_api.utils import Storage, audit
from ecnt_core.config import PROCESSED

FILES = [
    ("caribe_modelado.csv", "Caribe — determinantes sociales y mortalidad ECNT (2018-2019)", "modelado"),
    ("caribe_panel_municipio_anio.csv", "Caribe — panel municipio-año 2018-2021", "panel"),
    ("externo_otras_regiones_modelado.csv", "Otras regiones — validación externa", "externo"),
]
FUENTE = "DANE: NBI CNPV 2018, proyecciones de población 2018-2042, EEVV defunciones Cuadro 5 (definitivas)"
CONFIG = {"selection": "ranking_top_k", "select_k": 8, "cv_repeats": 3, "tune": True, "ratio": "80/20", "seed": 42}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aprobar-y-publicar", action="store_true")
    args = ap.parse_args()
    settings = get_settings()
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    SessionLocal = make_sessionmaker(engine)
    bootstrap(SessionLocal, settings)
    storage = Storage(settings.storage_dir)

    with SessionLocal() as db:
        admin = db.scalars(select(Usuario).where(Usuario.rol == "admin")).first()
        versions = {}
        for fname, nombre, rol in FILES:
            existing = db.scalars(select(Dataset).where(Dataset.rol == rol)).first()
            if existing:
                print(f"= Ya existe dataset '{rol}' (id {existing.id}); se reutiliza")
                versions[rol] = existing.versiones[-1]
                continue
            content = (PROCESSED / fname).read_bytes()
            ds, v = datasets.create_from_upload(db, storage, admin, content, fname, nombre, FUENTE,
                                                "Construido con scripts/construir_dataset_caribe.py", rol)
            audit(db, admin, "cargar_dataset", f"dataset:{ds.id}", {"archivo": fname, "script": True})
            versions[rol] = v
            print(f"+ Dataset {rol}: id {ds.id}, {v.filas} filas")
        db.commit()

        print("Entrenando y comparando modelos (puede tardar ~1-2 min)…")
        out = modeling.compare(db, storage, admin, versions["modelado"], CONFIG,
                               ["baseline", "linear", "ridge", "random_forest", "gradient_boosting"])
        db.commit()
        for r in out["tabla"]:
            print(f"  {r['algoritmo']:<18} RMSE CV {r['rmse_cv_media']:6.2f} ± {r['rmse_cv_de']:5.2f} | "
                  f"RMSE prueba {r['rmse_test']:6.2f} | R² prueba {r['r2_test']:5.2f}")
        print("Selección:", out["seleccion"]["razon"])

        if args.aprobar_y_publicar and out["seleccion"]["elegido"]:
            mid = next(r["version_modelo_id"] for r in out["tabla"] if r["algoritmo"] == out["seleccion"]["elegido"])
            mv = db.get(VersionModelo, mid)
            nota = ("Aprobado por el administrador mediante script de carga inicial. " + out["seleccion"]["razon"])
            modeling.approve(db, mv, admin, nota)
            audit(db, admin, "aprobar_modelo", f"modelo:{mv.id}", {"justificacion": nota, "script": True})
            res = modeling.publish(db, storage, mv, admin)
            res["alertas"] = alerts.generate(db, mv, admin)
            audit(db, admin, "publicar_modelo", f"modelo:{mv.id}", {**res, "script": True})
            db.commit()
            print(f"Publicado modelo {mv.id}: {res}")


if __name__ == "__main__":
    main()
