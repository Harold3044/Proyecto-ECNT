"""Datasets versionados: el original es inmutable; cada cambio crea una versión con linaje."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from ecnt_api.orm import Dataset, DatasetVersion, Usuario
from ecnt_api.utils import Storage, clean_json
from ecnt_core import cleaning
from ecnt_core.io import dataframe_sha256, file_sha256, normalize_codes, read_table
from ecnt_core.validation import validate


class DatasetValidationError(ValueError):
    def __init__(self, report: dict):
        super().__init__("El dataset no superó la validación")
        self.report = report


def load_df(storage: Storage, version: DatasetVersion) -> pd.DataFrame:
    return pd.read_parquet(storage.abs(version.ruta))


def _write_version(db: Session, storage: Storage, ds: Dataset, df: pd.DataFrame, user: Usuario,
                   parent: DatasetVersion | None, ops: list, desc: str) -> DatasetVersion:
    report = validate(df)
    if not report.is_valid:
        raise DatasetValidationError(clean_json(report.to_dict()))
    numero = (max((v.numero for v in ds.versiones), default=0)) + 1
    path = storage.dataset_dir(ds.id) / f"v{numero}.parquet"
    df.to_parquet(path, index=False)
    v = DatasetVersion(dataset_id=ds.id, numero=numero, padre_id=parent.id if parent else None, descripcion=desc,
                       operaciones=clean_json(ops), ruta=storage.rel(path), filas=len(df), columnas=df.shape[1],
                       sha256=dataframe_sha256(df), validacion=clean_json(report.to_dict()), creado_por=user.id)
    db.add(v)
    db.flush()
    db.refresh(ds)
    return v


def _flag_synthetic(df: pd.DataFrame, es_sintetico: bool) -> pd.DataFrame:
    if "es_sintetico" not in df.columns:
        df = df.assign(es_sintetico=es_sintetico)
    return df


def create_from_upload(db: Session, storage: Storage, user: Usuario, content: bytes, filename: str, nombre: str,
                       fuente: str = "", descripcion: str = "", rol: str | None = None,
                       es_sintetico: bool = False, sheet: str | int | None = 0) -> tuple[Dataset, DatasetVersion]:
    df = _flag_synthetic(read_table(content, filename, sheet), es_sintetico)
    report = validate(df)
    if not report.is_valid:  # no se guarda nada si hay errores bloqueantes
        raise DatasetValidationError(clean_json(report.to_dict()))
    es_sint = es_sintetico or df["es_sintetico"].astype(str).str.lower().isin(["true", "1"]).any()
    ds = Dataset(nombre=nombre, descripcion=descripcion, fuente=fuente, origen="archivo", rol=rol,
                 es_sintetico=bool(es_sint), sha256_original=file_sha256(content), creado_por=user.id)
    db.add(ds)
    db.flush()
    original = storage.dataset_dir(ds.id) / f"original_{filename.replace('/', '_').replace(chr(92), '_')}"
    original.write_bytes(content)
    ds.archivo_original = storage.rel(original)
    v = _write_version(db, storage, ds, df, user, None,
                       [{"op": "carga_original", "archivo": filename, "sha256": ds.sha256_original}],
                       "Versión original (sin modificaciones)")
    return ds, v


def create_from_records(db: Session, storage: Storage, user: Usuario, records: list[dict], nombre: str,
                        fuente: str = "", descripcion: str = "", rol: str | None = None,
                        es_sintetico: bool = False) -> tuple[Dataset, DatasetVersion]:
    df = _flag_synthetic(normalize_codes(pd.DataFrame(records)), es_sintetico)
    ds = Dataset(nombre=nombre, descripcion=descripcion, fuente=fuente, origen="formulario", rol=rol,
                 es_sintetico=es_sintetico, creado_por=user.id)
    db.add(ds)
    db.flush()
    v = _write_version(db, storage, ds, df, user, None, [{"op": "registro_formulario", "registros": len(df)}],
                       "Creado desde formulario")
    return ds, v


def add_records(db: Session, storage: Storage, user: Usuario, version: DatasetVersion,
                records: list[dict]) -> DatasetVersion:
    base = load_df(storage, version)
    new = normalize_codes(pd.DataFrame(records))
    unknown = [c for c in new.columns if c not in base.columns]
    if unknown:
        raise DatasetValidationError({"is_valid": False, "issues": [
            {"level": "error", "code": "columna_desconocida", "message": f"Columnas no presentes: {unknown}"}]})
    if "es_sintetico" in base.columns and "es_sintetico" not in new.columns:
        new["es_sintetico"] = bool(version.dataset.es_sintetico)
    df = pd.concat([base, new], ignore_index=True)
    return _write_version(db, storage, version.dataset, df, user, version,
                          [{"op": "registro_formulario", "registros": len(new)}],
                          f"Se agregaron {len(new)} registro(s) desde formulario")


def clean_version(db: Session, storage: Storage, user: Usuario, version: DatasetVersion, steps: list[dict],
                  descripcion: str = "") -> DatasetVersion:
    df, log = cleaning.apply_steps(load_df(storage, version), steps)
    return _write_version(db, storage, version.dataset, df, user, version, log,
                          descripcion or f"Limpieza: {', '.join(s['op'] for s in steps)}")


def latest_version_by_role(db: Session, rol: str) -> DatasetVersion | None:
    ds = db.scalars(select(Dataset).where(Dataset.rol == rol).order_by(Dataset.id.desc())).first()
    return ds.versiones[-1] if ds and ds.versiones else None


def dataset_dict(ds: Dataset) -> dict:
    return {
        "id": ds.id, "nombre": ds.nombre, "descripcion": ds.descripcion, "fuente": ds.fuente, "origen": ds.origen,
        "rol": ds.rol, "es_sintetico": ds.es_sintetico, "sha256_original": ds.sha256_original,
        "creado": ds.creado, "creado_por": ds.creado_por,
        "versiones": [version_dict(v, brief=True) for v in ds.versiones],
    }


def version_dict(v: DatasetVersion, brief: bool = False) -> dict:
    d = {"id": v.id, "dataset_id": v.dataset_id, "numero": v.numero, "padre_id": v.padre_id,
         "descripcion": v.descripcion, "filas": v.filas, "columnas": v.columnas, "sha256": v.sha256,
         "creado": v.creado}
    if not brief:
        d["operaciones"] = v.operaciones
        d["validacion"] = v.validacion
    return clean_json(d)
