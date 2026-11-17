"""Punto de entrada de la API. En el Bloque A solo expone el chequeo de salud."""

from fastapi import FastAPI

import ecnt_core

app = FastAPI(title="Plataforma ECNT — API", version=ecnt_core.__version__)


@app.get("/health", tags=["sistema"])
def health() -> dict[str, str]:
    """Verifica que la API esté en ejecución."""
    return {"status": "ok", "version": ecnt_core.__version__}
