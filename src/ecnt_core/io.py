"""Lectura de archivos tabulares cargados por los usuarios (CSV y Excel)."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pandas as pd

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
MAX_BYTES = 25 * 1024 * 1024
_TEXT_COLUMNS = {"divipola": 5, "cod_depto": 2}


class DataFileError(ValueError):
    """Error de formato o contenido en un archivo cargado."""


def file_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def normalize_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Asegura que los códigos DIVIPOLA sean texto y restaura el cero inicial que Excel suele eliminar
    (``8001`` → ``08001``). Solo se rellena UN dígito: un código más corto se deja tal cual para que la
    validación lo reporte como inválido (no se "corrigen" silenciosamente datos erróneos)."""
    df = df.copy()
    for col, width in _TEXT_COLUMNS.items():
        if col in df.columns:
            s = df[col]
            if pd.api.types.is_float_dtype(s):
                s = s.astype("Int64")
            s = s.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
            lost_zero = s.str.fullmatch(rf"\d{{{width - 1}}}").fillna(False)
            df[col] = s.mask(lost_zero, "0" + s)
    return df


def read_table(content: bytes, filename: str, sheet: str | int | None = 0) -> pd.DataFrame:
    """Lee un CSV o Excel desde bytes. Detecta separador y codificación de los CSV.

    Lanza :class:`DataFileError` con un mensaje comprensible si el archivo no es válido.
    """
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise DataFileError(f"Extensión '{ext}' no permitida. Use: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    if len(content) == 0:
        raise DataFileError("El archivo está vacío.")
    if len(content) > MAX_BYTES:
        raise DataFileError(f"El archivo supera el máximo de {MAX_BYTES // (1024 * 1024)} MB.")
    dtype = {c: str for c in _TEXT_COLUMNS}
    try:
        if ext == ".csv":
            df = None
            for enc in ("utf-8-sig", "latin-1"):
                try:
                    df = pd.read_csv(io.BytesIO(content), sep=None, engine="python", encoding=enc, dtype=dtype)
                    break
                except UnicodeDecodeError:
                    continue
            if df is None:
                raise DataFileError("No se pudo decodificar el CSV (use UTF-8 o Latin-1).")
        else:
            df = pd.read_excel(io.BytesIO(content), sheet_name=sheet, dtype=dtype)
    except DataFileError:
        raise
    except Exception as exc:  # pandas lanza varios tipos según el formato
        raise DataFileError(f"No se pudo leer el archivo: {exc}") from exc
    df.columns = [str(c).strip() for c in df.columns]
    if df.shape[1] == 0 or df.shape[0] == 0:
        raise DataFileError("El archivo no contiene filas o columnas de datos.")
    return normalize_codes(df)


def read_path(path: str | Path, sheet: str | int | None = 0) -> pd.DataFrame:
    path = Path(path)
    return read_table(path.read_bytes(), path.name, sheet)


def dataframe_sha256(df: pd.DataFrame) -> str:
    """Huella reproducible del contenido de un DataFrame."""
    return hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()
