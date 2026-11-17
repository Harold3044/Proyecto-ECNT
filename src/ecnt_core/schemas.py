"""Esquema canónico de una observación territorial.

Una observación = un territorio (municipio, DIVIPOLA de 5 dígitos) en un periodo.
Las columnas desconocidas se aceptan (se reportan como "no catalogadas"), pero las
columnas que parecen datos personales se rechazan.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ecnt_core.sources.dane import NBI_AREAS, NBI_VARS


@dataclass(frozen=True)
class VariableSpec:
    name: str
    kind: str  # "id" | "numeric" | "categorical" | "target" | "meta"
    description: str
    unit: str = ""
    min: float | None = None
    max: float | None = None
    is_predictor: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


_AREA_LABEL = {"total": "total municipal", "cab": "cabeceras", "resto": "centros poblados y rural disperso"}
_NBI_LABEL = {
    "nbi": "Personas con NBI",
    "miseria": "Personas en miseria",
    "comp_vivienda": "Componente vivienda inadecuada",
    "comp_servicios": "Componente servicios (agua y saneamiento)",
    "comp_hacinamiento": "Componente hacinamiento",
    "comp_inasistencia": "Componente inasistencia escolar",
    "comp_dependencia": "Componente dependencia económica",
}

_specs: list[VariableSpec] = [
    VariableSpec("divipola", "id", "Código DIVIPOLA del municipio (5 dígitos)"),
    VariableSpec("cod_depto", "id", "Código DIVIPOLA del departamento (2 dígitos)"),
    VariableSpec("departamento", "categorical", "Nombre del departamento"),
    VariableSpec("municipio", "id", "Nombre del municipio"),
    VariableSpec("periodo", "id", "Periodo de la observación (año o rango de años)"),
    VariableSpec("region", "categorical", "Región"),
    VariableSpec("poblacion_2018", "numeric", "Población total 2018 (proyección DANE)", "personas", 0, None, True),
    VariableSpec("pct_poblacion_resto", "numeric", "Población en centros poblados y rural disperso", "%", 0, 100,
                 True),
    VariableSpec("pct_65_mas", "numeric", "Población de 65 años y más", "%", 0, 100, True),
    VariableSpec("pct_0_14", "numeric", "Población de 0 a 14 años", "%", 0, 100, True),
    VariableSpec("def_ecnt_2018_2019", "numeric", "Defunciones por ECNT cardiometabólicas 2018-2019",
                 "defunciones", 0, None),
    VariableSpec("personas_anio_2018_2019", "numeric", "Personas-año de exposición 2018-2019", "personas-año",
                 0, None),
    VariableSpec("anios_con_registro", "numeric", "Años con registro de defunciones", "años", 0, 10),
    VariableSpec("tasa_mort_ecnt_std", "target",
                 "Mortalidad por ECNT cardiometabólicas estandarizada por edad (2018-2019)",
                 "por 100.000 hab.", 0, 2000),
    VariableSpec("es_sintetico", "meta", "Indica si la fila es sintética (no real)"),
]
for _a in NBI_AREAS:
    for _v in NBI_VARS:
        _specs.append(
            VariableSpec(f"{_v}_{_a}", "numeric", f"{_NBI_LABEL[_v]} — {_AREA_LABEL[_a]} (NBI CNPV 2018)",
                         "%", 0, 100, True)
        )

CANONICAL: dict[str, VariableSpec] = {s.name: s for s in _specs}
DEFAULT_TARGET = "tasa_mort_ecnt_std"
DEFAULT_KEY = ("divipola", "periodo")
REQUIRED_COLUMNS = ("divipola",)
DEFAULT_PREDICTORS = [s.name for s in _specs if s.is_predictor]
# Columnas que nunca deben usarse como predictoras (identificadores, derivadas del objetivo)
NON_PREDICTORS = {
    "divipola", "cod_depto", "municipio", "periodo", "es_sintetico", "region",
    "def_ecnt_2018_2019", "personas_anio_2018_2019", "anios_con_registro", DEFAULT_TARGET,
}

# Patrones de nombres de columna que sugieren datos personales (se rechazan en la carga)
SENSITIVE_PATTERNS = (
    "documento", "cedula", "cédula", "identificacion", "identificación", "num_id", "tipo_id", "paciente",
    "nombre_persona", "nombres", "apellido", "telefono", "teléfono", "celular", "direccion", "dirección",
    "correo", "email", "fecha_nacimiento", "historia_clinica", "historia_clínica",
)
