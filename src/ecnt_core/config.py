"""Constantes compartidas: territorio de estudio, grupos de edad y definición de ECNT."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
SYNTHETIC = DATA / "synthetic"

SEED = 42

# Región Caribe: códigos DIVIPOLA de departamento
CARIBE_DEPTOS: dict[str, str] = {
    "08": "Atlántico",
    "13": "Bolívar",
    "20": "Cesar",
    "23": "Córdoba",
    "44": "La Guajira",
    "47": "Magdalena",
    "70": "Sucre",
    "88": "San Andrés, Providencia y Santa Catalina",
}

# Grupos de edad publicados por el DANE en el Cuadro 5 de defunciones no fetales.
# (etiqueta, edad mínima, edad máxima inclusive); 100 = "100 y más".
AGE_GROUPS: list[tuple[str, int, int]] = [
    ("0", 0, 0),
    ("1-4", 1, 4),
    ("5-14", 5, 14),
    ("15-44", 15, 44),
    ("45-64", 45, 64),
    ("65-84", 65, 84),
    ("85-99", 85, 99),
    ("100+", 100, 100),
]
AGE_LABELS = [g[0] for g in AGE_GROUPS]

# Definición operativa de ECNT cardiometabólicas con la lista 6/67 CIE-10 de la OPS.
# Se excluye 301 (fiebre reumática: origen infeccioso).
ECNT_CAUSES: dict[str, str] = {
    "302": "Enfermedades hipertensivas",
    "303": "Enfermedades isquémicas del corazón",
    "304": "Enfermedad cardiopulmonar y otras formas de enfermedad del corazón",
    "306": "Insuficiencia cardíaca",
    "307": "Enfermedades cerebrovasculares",
    "309": "Las demás enfermedades del sistema circulatorio",
    "601": "Diabetes mellitus",
}
