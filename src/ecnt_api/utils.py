"""Utilidades: JSON seguro, auditoría y almacenamiento de archivos."""

from __future__ import annotations

import math
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import Request
from sqlalchemy.orm import Session

from ecnt_api.orm import Auditoria, Usuario


def clean_json(obj):
    """Convierte tipos numpy/pandas y reemplaza NaN/inf por None (JSON válido)."""
    if isinstance(obj, dict):
        return {str(k): clean_json(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple | set):
        return [clean_json(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, float | np.floating):
        f = float(obj)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return clean_json(obj.tolist())
    if isinstance(obj, pd.DataFrame):
        return clean_json(obj.to_dict("records"))
    if isinstance(obj, datetime | date | pd.Timestamp):
        return obj.isoformat()
    if obj is pd.NA or obj is pd.NaT:
        return None
    return obj


def audit(db: Session, user: Usuario | None, action: str, resource: str, detail: dict | None = None,
          request: Request | None = None) -> None:
    db.add(Auditoria(
        usuario_id=user.id if user else None, usuario_email=user.email if user else None, accion=action,
        recurso=resource, detalle=clean_json(detail or {}),
        ip=request.client.host if request is not None and request.client else None,
    ))


class Storage:
    """Rutas de archivos bajo ECNT_STORAGE_DIR."""

    def __init__(self, root: Path):
        self.root = Path(root)
        for sub in ("datasets", "modelos"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    def dataset_dir(self, dataset_id: int) -> Path:
        p = self.root / "datasets" / str(dataset_id)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def model_dir(self, experiment_id: int) -> Path:
        return self.root / "modelos" / f"exp_{experiment_id}"

    def rel(self, p: Path) -> str:
        return Path(p).relative_to(self.root).as_posix()

    def abs(self, rel: str) -> Path:
        p = (self.root / rel).resolve()
        if self.root.resolve() not in p.parents and p != self.root.resolve():
            raise ValueError("Ruta fuera del almacenamiento")
        return p
