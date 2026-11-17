"""Validación de datasets territoriales: formato, tipos, rangos, llaves y datos sensibles."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import pandas as pd

from ecnt_core.schemas import CANONICAL, DEFAULT_KEY, REQUIRED_COLUMNS, SENSITIVE_PATTERNS, VariableSpec

ERROR, WARNING, INFO = "error", "warning", "info"


@dataclass
class Issue:
    level: str
    code: str
    message: str
    column: str | None = None
    count: int = 0
    examples: list = field(default_factory=list)


@dataclass
class ColumnInfo:
    name: str
    dtype: str
    kind: str  # numérica / categórica / identificador / objetivo / desconocida
    catalogada: bool
    nulos: int
    unicos: int


@dataclass
class ValidationReport:
    n_rows: int
    n_cols: int
    issues: list[Issue]
    columns: list[ColumnInfo]

    @property
    def is_valid(self) -> bool:
        return not any(i.level == ERROR for i in self.issues)

    def to_dict(self) -> dict:
        return {
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "is_valid": self.is_valid,
            "issues": [asdict(i) for i in self.issues],
            "columns": [asdict(c) for c in self.columns],
        }


def _is_sensitive(col: str) -> bool:
    c = col.lower().replace(" ", "_")
    return any(p in c for p in SENSITIVE_PATTERNS)


def _column_kind(name: str, s: pd.Series, spec: VariableSpec | None) -> str:
    if spec is not None:
        return {"id": "identificador", "numeric": "numérica", "categorical": "categórica",
                "target": "objetivo", "meta": "metadato"}[spec.kind]
    return "numérica" if pd.api.types.is_numeric_dtype(s) else "categórica"


def _examples(index: pd.Index, n: int = 5) -> list:
    return [int(i) if isinstance(i, int | float) else str(i) for i in list(index[:n])]


def validate(
    df: pd.DataFrame,
    key: tuple[str, ...] = DEFAULT_KEY,
    required: tuple[str, ...] = REQUIRED_COLUMNS,
    schema: dict[str, VariableSpec] = CANONICAL,
    insufficient_threshold: float = 0.5,
) -> ValidationReport:
    """Valida un DataFrame y devuelve un reporte con errores (bloquean) y advertencias (se pueden limpiar)."""
    issues: list[Issue] = []
    n = len(df)
    if n == 0:
        issues.append(Issue(ERROR, "vacio", "El dataset no tiene filas."))

    dup_cols = df.columns[df.columns.duplicated()].tolist()
    if dup_cols:
        issues.append(Issue(ERROR, "columnas_duplicadas", f"Columnas repetidas: {dup_cols}", count=len(dup_cols)))

    for col in df.columns:
        if _is_sensitive(col):
            issues.append(Issue(ERROR, "dato_personal",
                                f"La columna '{col}' parece contener datos personales. La plataforma solo "
                                "acepta información territorial agregada.", column=col))

    for col in required:
        if col not in df.columns:
            issues.append(Issue(ERROR, "columna_requerida", f"Falta la columna obligatoria '{col}'.", column=col))

    if "divipola" in df.columns:
        bad = df["divipola"].astype("string").str.fullmatch(r"\d{5}").fillna(False) == False  # noqa: E712
        if bad.any():
            issues.append(Issue(ERROR, "divipola_invalido", "Códigos DIVIPOLA que no tienen 5 dígitos.",
                                "divipola", int(bad.sum()), _examples(df.index[bad])))

    if n:
        full_dup = df.duplicated()
        if full_dup.any():
            issues.append(Issue(WARNING, "filas_duplicadas", "Filas idénticas repetidas.", count=int(full_dup.sum()),
                                examples=_examples(df.index[full_dup])))
        key_cols = [k for k in key if k in df.columns]
        if key_cols:
            key_dup = df.duplicated(subset=key_cols, keep=False) & ~df.duplicated(keep=False)
            if key_dup.any():
                issues.append(Issue(WARNING, "llave_duplicada",
                                    f"Registros distintos con la misma llave {key_cols} (inconsistencia).",
                                    count=int(key_dup.sum()), examples=_examples(df.index[key_dup])))

    columns: list[ColumnInfo] = []
    for col in df.columns:
        s = df[col]
        spec = schema.get(col)
        nulls = int(s.isna().sum())
        columns.append(ColumnInfo(col, str(s.dtype), _column_kind(col, s, spec), spec is not None, nulls,
                                  int(s.nunique(dropna=True))))
        if spec is None and col not in required:
            issues.append(Issue(INFO, "no_catalogada", f"Columna '{col}' no está en el diccionario canónico.",
                                column=col))
        if n and nulls:
            frac = nulls / n
            level = WARNING if frac >= insufficient_threshold else INFO
            code = "informacion_insuficiente" if frac >= insufficient_threshold else "nulos"
            issues.append(Issue(level, code, f"{nulls} valores nulos ({frac:.0%}).", col, nulls,
                                _examples(df.index[s.isna()])))
        if n > 1 and s.nunique(dropna=True) == 1:
            issues.append(Issue(WARNING, "constante", f"La columna '{col}' tiene un único valor.", column=col))

        if spec is not None and spec.kind in ("numeric", "target"):
            num = pd.to_numeric(s, errors="coerce")
            bad_type = num.isna() & s.notna()
            if bad_type.any():
                issues.append(Issue(WARNING, "tipo_incorrecto", "Valores no numéricos en una variable numérica.",
                                    col, int(bad_type.sum()), [str(v) for v in s[bad_type].head(5)]))
            out = pd.Series(False, index=s.index)
            if spec.min is not None:
                out |= num < spec.min
            if spec.max is not None:
                out |= num > spec.max
            if out.any():
                issues.append(Issue(WARNING, "fuera_de_rango",
                                    f"Valores fuera del rango [{spec.min}, {spec.max}] {spec.unit}.", col,
                                    int(out.sum()), _examples(df.index[out])))

    if "es_sintetico" in df.columns and df["es_sintetico"].astype(str).str.lower().isin(["true", "1"]).any():
        issues.append(Issue(INFO, "sintetico", "El dataset contiene filas SINTÉTICAS (no reales)."))

    return ValidationReport(n, df.shape[1], issues, columns)
