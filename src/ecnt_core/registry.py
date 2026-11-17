"""Exportación, versionado y uso de modelos entrenados.

Un *bundle* es una carpeta con ``model.joblib`` (pipeline completo, incluye las
transformaciones) y ``metadata.json`` (configuración, métricas, variables, huellas).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ecnt_core.experiment import ExperimentResult


class ModelBundleError(ValueError):
    pass


@dataclass
class ModelBundle:
    pipeline: object
    metadata: dict

    @property
    def features(self) -> list[str]:
        return list(self.metadata["variables"]) + list(self.metadata.get("variables_categoricas", []))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonable(o):
    if isinstance(o, np.integer | np.floating):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, pd.Timestamp | datetime):
        return o.isoformat()
    raise TypeError(f"No serializable: {type(o)}")


def save_bundle(result: ExperimentResult, out_dir: str | Path, version: str, extra: dict | None = None) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    model_path = out / "model.joblib"
    joblib.dump(result.pipeline, model_path)
    meta = {
        "version": version,
        "creado": datetime.now(UTC).isoformat(timespec="seconds"),
        "config": result.config,
        **result.summary,
        "sha256_modelo": _sha256(model_path),
        **(extra or {}),
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False, default=_jsonable), "utf-8")
    return out


def load_bundle(path: str | Path) -> ModelBundle:
    path = Path(path)
    meta = json.loads((path / "metadata.json").read_text("utf-8"))
    model_path = path / "model.joblib"
    if _sha256(model_path) != meta["sha256_modelo"]:
        raise ModelBundleError("La huella del archivo del modelo no coincide: posible alteración.")
    return ModelBundle(joblib.load(model_path), meta)


def predict(bundle: ModelBundle, df: pd.DataFrame, id_cols: tuple[str, ...] = ("divipola", "municipio",
                                                                                 "departamento", "periodo")
            ) -> pd.DataFrame:
    """Aplica el pipeline (con sus transformaciones ajustadas en entrenamiento) a datos nuevos.

    Valida que estén todas las variables. Devuelve predicción e intervalo empírico del 90 %.
    """
    missing = [c for c in bundle.features if c not in df.columns]
    if missing:
        raise ModelBundleError(f"Faltan variables requeridas por el modelo: {missing}")
    X = df[bundle.features].copy()
    for c in bundle.metadata["variables"]:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    pred = bundle.pipeline.predict(X)
    q = float(bundle.metadata.get("semiancho_intervalo_90", np.nan))
    out = df[[c for c in id_cols if c in df.columns]].copy()
    out["prediccion"] = pred
    out["lim_inf_90"] = np.maximum(pred - q, 0)  # una tasa no puede ser negativa
    out["lim_sup_90"] = pred + q
    out["variables_imputadas"] = X[bundle.metadata["variables"]].isna().sum(axis=1).values
    out["version_modelo"] = bundle.metadata["version"]
    return out.reset_index(drop=True)
