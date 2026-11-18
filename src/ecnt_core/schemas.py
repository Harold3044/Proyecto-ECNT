"""Esquema canónico y DICCIONARIO DE VARIABLES de una observación territorial.

Una observación = un territorio (municipio, DIVIPOLA de 5 dígitos) en un periodo.
Este módulo es la fuente única de las descripciones de variables que muestran la API, las
aplicaciones y la documentación (``scripts/generar_diccionario.py`` produce el Markdown).
Las columnas desconocidas se aceptan (se reportan como "no catalogadas"); las que parecen
datos personales se rechazan.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from ecnt_core.sources.dane import NBI_AREAS, NBI_VARS


@dataclass(frozen=True)
class VariableSpec:
    name: str
    kind: str  # "id" | "numeric" | "categorical" | "target" | "meta"
    description: str  # nombre corto legible
    unit: str = ""
    min: float | None = None
    max: float | None = None
    is_predictor: bool = False
    explicacion: str = ""  # qué significa, en lenguaje sencillo
    fuente: str = ""
    grupo: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


DANE_NBI = "DANE — Censo Nacional de Población y Vivienda 2018, anexo NBI municipal"
DANE_PROY = "DANE — Proyecciones de población municipal por área, sexo y edad 2018-2042"
DANE_EEVV = "DANE — Estadísticas Vitales, defunciones no fetales (Cuadro 5, cifras definitivas)"
CALC = "Calculada por el proyecto"

_AREA = {
    "total": ("total municipal", "en todo el municipio (cabecera más zona rural)"),
    "cab": ("cabecera", "solo en la cabecera municipal (casco urbano)"),
    "resto": ("centros poblados y rural disperso",
              "solo fuera de la cabecera: centros poblados (caseríos, corregimientos) y zona rural dispersa "
              "(viviendas aisladas en el campo). El DANE publica estas dos zonas juntas"),
}
_NBI = {
    "nbi": ("Personas con NBI",
            "Porcentaje de personas que viven en hogares con AL MENOS UNA necesidad básica insatisfecha (vivienda "
            "inadecuada, servicios inadecuados, hacinamiento crítico, inasistencia escolar o alta dependencia "
            "económica). Es el indicador resumen de pobreza estructural del DANE: a mayor valor, más pobreza."),
    "miseria": ("Personas en miseria",
                "Porcentaje de personas que viven en hogares con DOS O MÁS necesidades básicas insatisfechas al "
                "mismo tiempo. Mide la pobreza más severa."),
    "comp_vivienda": ("Vivienda inadecuada",
                      "Porcentaje de personas en viviendas con condiciones físicas impropias para habitar: piso de "
                      "tierra, paredes de materiales precarios (tela, cartón, desechos) o sin paredes."),
    "comp_servicios": ("Servicios inadecuados (agua y saneamiento)",
                       "Porcentaje de personas en viviendas SIN SANITARIO o SIN ACUEDUCTO que se abastecen de agua de "
                       "río, nacimiento, carrotanque o lluvia. Es el determinante de AGUA POTABLE y SANEAMIENTO "
                       "BÁSICO del proyecto."),
    "comp_hacinamiento": ("Hacinamiento crítico",
                          "Porcentaje de personas en hogares donde duermen MÁS DE TRES PERSONAS POR CUARTO (sin contar "
                          "cocina, baño ni garaje)."),
    "comp_inasistencia": ("Inasistencia escolar",
                          "Porcentaje de personas en hogares con al menos un niño de 6 a 12 años que NO ASISTE a un "
                          "centro educativo. Es uno de los determinantes de EDUCACIÓN del proyecto."),
    "comp_dependencia": ("Alta dependencia económica",
                         "Porcentaje de personas en hogares con MÁS DE TRES PERSONAS POR CADA OCUPADO y cuyo jefe de "
                         "hogar tiene como máximo dos años de primaria aprobados. Combina ingreso (pocos ocupados) y "
                         "EDUCACIÓN (baja escolaridad del jefe)."),
}

_specs: list[VariableSpec] = [
    VariableSpec("divipola", "id", "Código DIVIPOLA del municipio", grupo="Identificación", fuente="DANE",
                 explicacion="Código oficial del DANE que identifica cada municipio de Colombia: 2 dígitos del "
                             "departamento + 3 del municipio (p. ej. 20001 = Valledupar, Cesar). Es la llave que "
                             "une todas las fuentes. Se guarda como texto para no perder el cero inicial (08001)."),
    VariableSpec("cod_depto", "id", "Código del departamento", grupo="Identificación", fuente="DANE",
                 explicacion="Dos primeros dígitos del DIVIPOLA: 08 Atlántico, 13 Bolívar, 20 Cesar, 23 Córdoba, "
                             "44 La Guajira, 47 Magdalena, 70 Sucre, 88 San Andrés."),
    VariableSpec("departamento", "categorical", "Departamento", grupo="Identificación", fuente="DANE",
                 explicacion="Nombre del departamento al que pertenece el municipio."),
    VariableSpec("municipio", "id", "Municipio", grupo="Identificación", fuente="DANE",
                 explicacion="Nombre del municipio. Puede repetirse en distintos departamentos (p. ej. Villanueva); "
                             "por eso la llave es el DIVIPOLA."),
    VariableSpec("periodo", "id", "Periodo", grupo="Identificación", fuente=CALC,
                 explicacion="Años que cubre la observación. '2018-2019' significa que la mortalidad se calculó "
                             "sumando las defunciones y la población de esos dos años."),
    VariableSpec("region", "categorical", "Región", grupo="Identificación", fuente=CALC,
                 explicacion="'Caribe' para los municipios del estudio; 'Otras regiones' para los municipios del "
                             "resto del país usados solo como datos independientes de validación externa."),
    VariableSpec("poblacion_2018", "numeric", "Población total 2018", "personas", 0, None, True, grupo="Demografía",
                 fuente=DANE_PROY,
                 explicacion="Número de habitantes del municipio en 2018. Indica el tamaño del territorio; en "
                             "municipios pequeños las tasas son menos estables."),
    VariableSpec("pct_poblacion_resto", "numeric", "Población en zona rural (centros poblados y rural disperso)", "%",
                 0, 100, True, grupo="Demografía", fuente=f"{CALC} con {DANE_PROY}",
                 explicacion="Porcentaje de los habitantes que vive FUERA DE LA CABECERA municipal (centros poblados y "
                             "zona rural dispersa). Es la medida de RURALIDAD / DISPERSIÓN del proyecto: 80 % "
                             "significa que 8 de cada 10 personas viven en el campo o en caseríos."),
    VariableSpec("pct_65_mas", "numeric", "Población de 65 años y más", "%", 0, 100, True, grupo="Demografía",
                 fuente=f"{CALC} con {DANE_PROY}",
                 explicacion="Porcentaje de adultos mayores. Las ECNT aumentan mucho con la edad; esta variable "
                             "describe el envejecimiento del municipio (la tasa objetivo ya está ajustada por edad)."),
    VariableSpec("pct_0_14", "numeric", "Población de 0 a 14 años", "%", 0, 100, True, grupo="Demografía",
                 fuente=f"{CALC} con {DANE_PROY}",
                 explicacion="Porcentaje de niños y adolescentes. Un valor alto indica una población joven."),
    VariableSpec("def_ecnt_2018_2019", "numeric", "Defunciones por ECNT 2018-2019", "defunciones", 0, None,
                 grupo="Resultado de salud", fuente=DANE_EEVV,
                 explicacion="Número total de personas residentes en el municipio que murieron por ECNT "
                             "cardiometabólicas en 2018 y 2019 (hipertensión, infarto e isquemia, insuficiencia "
                             "cardíaca, accidente cerebrovascular, otras circulatorias y diabetes). Sirve para "
                             "calcular la tasa; NO se usa como predictor."),
    VariableSpec("personas_anio_2018_2019", "numeric", "Personas-año de exposición 2018-2019", "personas-año", 0, None,
                 grupo="Resultado de salud", fuente=f"{CALC} con {DANE_PROY}",
                 explicacion="Suma de la población de 2018 y la de 2019. Es el denominador de la tasa (cuántas "
                             "personas estuvieron 'expuestas' durante los dos años)."),
    VariableSpec("anios_con_registro", "numeric", "Años con registro de defunciones", "años", 0, 10,
                 grupo="Resultado de salud", fuente=f"{CALC} con {DANE_EEVV}",
                 explicacion="Cuántos de los años del periodo tienen información de defunciones para el municipio. "
                             "Si falta algún año, la tasa no se calcula."),
    VariableSpec("tasa_mort_ecnt_std", "target",
                 "Mortalidad por ECNT estandarizada por edad (2018-2019)", "por 100.000 hab.", 0, 2000,
                 grupo="Variable objetivo", fuente=f"{CALC} con {DANE_EEVV} y {DANE_PROY}",
                 explicacion="VARIABLE QUE EL MODELO PREDICE. Muertes por ECNT cardiometabólicas por cada 100.000 "
                             "habitantes, AJUSTADA POR EDAD: se calcula como si todos los municipios tuvieran la "
                             "misma estructura de edades que Colombia en 2018, para que un municipio no salga 'peor' "
                             "solo por tener más adultos mayores. Ejemplo: 170 = 170 muertes por cada 100.000 "
                             "personas al año. Es mortalidad REGISTRADA: en zonas rurales dispersas puede haber "
                             "subregistro."),
    VariableSpec("es_sintetico", "meta", "¿Dato sintético?", grupo="Control", fuente=CALC,
                 explicacion="Verdadero si la fila fue generada artificialmente para pruebas (no es real). En los "
                             "datasets oficiales del proyecto siempre es Falso."),
]
for _a in NBI_AREAS:
    for _v in NBI_VARS:
        corto, largo = _NBI[_v]
        area_corta, area_larga = _AREA[_a]
        _specs.append(VariableSpec(
            f"{_v}_{_a}", "numeric", f"{corto} — {area_corta}", "%", 0, 100, True,
            grupo="Determinantes sociales (NBI 2018)", fuente=DANE_NBI,
            explicacion=f"{largo} Medido {area_larga}.",
        ))

CANONICAL: dict[str, VariableSpec] = {s.name: s for s in _specs}

# --- Columnas del panel municipio-año (evolución 2018-2021) -------------------------------------
_AGE_TXT = {"0": "menores de 1 año", "1-4": "de 1 a 4 años", "5-14": "de 5 a 14 años", "15-44": "de 15 a 44 años",
            "45-64": "de 45 a 64 años", "65-84": "de 65 a 84 años", "85-99": "de 85 a 99 años",
            "100+": "de 100 años y más", "desconocida": "con edad desconocida"}
PANEL: dict[str, VariableSpec] = {s.name: s for s in [
    VariableSpec("anio", "id", "Año", grupo="Identificación",
                 explicacion="Año calendario de la observación (2018-2021)."),
    VariableSpec("pob_total", "numeric", "Población total del año", "personas", 0, None, grupo="Demografía",
                 fuente=DANE_PROY, explicacion="Habitantes del municipio en ese año."),
    VariableSpec("pob_cabecera", "numeric", "Población en la cabecera", "personas", 0, None, grupo="Demografía",
                 fuente=DANE_PROY, explicacion="Habitantes del casco urbano."),
    VariableSpec("pob_resto", "numeric", "Población en centros poblados y rural disperso", "personas", 0, None,
                 grupo="Demografía", fuente=DANE_PROY, explicacion="Habitantes fuera de la cabecera (zona rural)."),
    VariableSpec("def_todas_causas", "numeric", "Defunciones por todas las causas", "defunciones", 0, None,
                 grupo="Resultado de salud", fuente=DANE_EEVV,
                 explicacion="Total de muertes de residentes del municipio en el año, por cualquier causa."),
    VariableSpec("def_ecnt", "numeric", "Defunciones por ECNT cardiometabólicas", "defunciones", 0, None,
                 grupo="Resultado de salud", fuente=DANE_EEVV,
                 explicacion="Muertes por hipertensión, enfermedad isquémica, insuficiencia cardíaca, enfermedad "
                             "cerebrovascular, otras circulatorias y diabetes en el año."),
    VariableSpec("def_hta", "numeric", "Defunciones por enfermedades hipertensivas", "defunciones", 0, None,
                 grupo="Resultado de salud", fuente=DANE_EEVV,
                 explicacion="Muertes por hipertensión arterial (código 302)."),
    VariableSpec("def_isquemica", "numeric", "Defunciones por enfermedad isquémica del corazón", "defunciones", 0, None,
                 grupo="Resultado de salud", fuente=DANE_EEVV,
                 explicacion="Infartos y otras isquemias (código 303)."),
    VariableSpec("def_cerebrovascular", "numeric", "Defunciones por enfermedad cerebrovascular", "defunciones", 0,
                 None, grupo="Resultado de salud", fuente=DANE_EEVV,
                 explicacion="Accidentes cerebrovasculares o 'derrames' (código 307)."),
    VariableSpec("def_diabetes", "numeric", "Defunciones por diabetes", "defunciones", 0, None,
                 grupo="Resultado de salud", fuente=DANE_EEVV,
                 explicacion="Muertes por diabetes mellitus (código 601)."),
    VariableSpec("registro_defunciones", "meta", "¿Hay registro de defunciones?", grupo="Control", fuente=DANE_EEVV,
                 explicacion="Verdadero si el DANE publicó defunciones para el municipio ese año."),
    VariableSpec("tasa_ecnt_cruda", "numeric", "Mortalidad por ECNT cruda", "por 100.000 hab.", 0, None,
                 grupo="Resultado de salud", fuente=CALC,
                 explicacion="Muertes por ECNT por cada 100.000 habitantes SIN ajustar por edad. Municipios con más "
                             "adultos mayores tienden a tener tasas crudas más altas."),
    VariableSpec("tasa_ecnt_std", "numeric", "Mortalidad por ECNT estandarizada por edad (anual)", "por 100.000 hab.",
                 0, None, grupo="Resultado de salud", fuente=CALC,
                 explicacion="Igual que la variable objetivo, pero para un solo año. Permite comparar municipios y "
                             "años sin el efecto de la estructura de edades."),
    VariableSpec("periodo_pandemia", "meta", "¿Año de pandemia?", grupo="Control", fuente=CALC,
                 explicacion="Verdadero para 2020 y 2021: la COVID-19 alteró la mortalidad y su registro; por eso "
                             "esos años no se usan en la variable objetivo."),
]}
for _g, _t in _AGE_TXT.items():
    if _g != "desconocida":
        PANEL[f"pob_{_g}"] = VariableSpec(f"pob_{_g}", "numeric", f"Población {_t}", "personas", 0, None,
                                          grupo="Demografía", fuente=DANE_PROY,
                                          explicacion=f"Habitantes {_t}. Se usa para ajustar la tasa por edad.")
    PANEL[f"def_{_g}"] = VariableSpec(f"def_{_g}", "numeric", f"Defunciones por ECNT {_t}", "defunciones", 0, None,
                                      grupo="Resultado de salud", fuente=DANE_EEVV,
                                      explicacion=f"Muertes por ECNT de personas {_t}. Se usa para ajustar la tasa "
                                                  "por edad.")

# Columnas que producen las predicciones y la interfaz EPS
OUTPUTS: dict[str, VariableSpec] = {s.name: s for s in [
    VariableSpec("predicho", "numeric", "Mortalidad esperada por el modelo", "por 100.000 hab.",
                 grupo="Resultado del modelo",
                 explicacion="Mortalidad por ECNT que el modelo estima según los determinantes sociales y "
                             "demográficos del municipio. Para municipios usados en el entrenamiento se calcula "
                             "'fuera de muestra' (sin que el modelo haya visto ese municipio)."),
    VariableSpec("observado", "numeric", "Mortalidad registrada", "por 100.000 hab.", grupo="Resultado del modelo",
                 explicacion="Mortalidad realmente registrada por el DANE (la variable objetivo)."),
    VariableSpec("lim_inf", "numeric", "Límite inferior del intervalo del 90 %", "por 100.000 hab.",
                 grupo="Resultado del modelo",
                 explicacion="Con 90 % de confianza, la mortalidad esperada no es menor a este valor. Si lo registrado "
                             "queda por debajo, puede haber subregistro."),
    VariableSpec("lim_sup", "numeric", "Límite superior del intervalo del 90 %", "por 100.000 hab.",
                 grupo="Resultado del modelo",
                 explicacion="Con 90 % de confianza, la mortalidad esperada no supera este valor. Si lo registrado "
                             "queda por encima, hay un exceso que amerita revisión."),
    VariableSpec("nivel", "categorical", "Nivel de mortalidad esperada", grupo="Resultado del modelo",
                 explicacion="Quintil del municipio dentro del Caribe según la mortalidad esperada: 'muy bajo' es el "
                             "20 % de municipios con valores más bajos y 'muy alto' el 20 % con valores más altos."),
    VariableSpec("poblacion", "numeric", "Población 2018", "personas", grupo="Resultado del modelo",
                 explicacion="Habitantes del municipio en 2018."),
]}

ALL_SPECS: dict[str, VariableSpec] = {**PANEL, **OUTPUTS, **CANONICAL}

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


def describe_column(name: str) -> dict:
    """Descripción legible de cualquier columna; las no catalogadas se marcan como tales."""
    spec = ALL_SPECS.get(name)
    if spec is None:
        log = re.fullmatch(r"(.+)_log", name)
        if log and log.group(1) in ALL_SPECS:
            base = ALL_SPECS[log.group(1)]
            exp = f"log(1 + x) de '{base.name}', creada en la limpieza para reducir la asimetría. "
            return {"variable": name, "descripcion": f"{base.description} (logaritmo)", "unidad": "",
                    "grupo": base.grupo, "explicacion": exp + base.explicacion, "fuente": base.fuente}
        return {"variable": name, "descripcion": name, "unidad": "", "grupo": "No catalogada", "fuente": "",
                "explicacion": "Columna no incluida en el diccionario del proyecto (agregada por el usuario o "
                               "creada en una transformación)."}
    return {"variable": name, "descripcion": spec.description, "unidad": spec.unit, "grupo": spec.grupo,
            "explicacion": spec.explicacion, "fuente": spec.fuente}


def dictionary_for(columns: list[str]) -> list[dict]:
    return [describe_column(c) for c in columns]
