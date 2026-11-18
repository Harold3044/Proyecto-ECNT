"""Selectores compartidos entre vistas del ambiente Administrador."""

from __future__ import annotations

import streamlit as st

from ecnt_client.ui import api, call


def datasets() -> list[dict]:
    return call(api().get, "/datasets") or []


def version_selector(key: str, label: str = "Dataset y versión") -> dict | None:
    """Selector dataset → versión. Devuelve la versión elegida (dict) o None."""
    ds = datasets()
    if not ds:
        st.info("No hay datasets cargados. Use **Carga masiva** o **Ingreso territorial**.")
        return None
    opts = {f"#{d['id']} · {d['nombre']}" + (" · SINTÉTICO" if d["es_sintetico"] else ""): d for d in ds}
    c1, c2 = st.columns([3, 1])
    d = opts[c1.selectbox(label, list(opts), key=f"{key}_ds")]
    versions = {f"v{v['numero']} · {v['filas']} filas · {v['descripcion'][:40]}": v for v in reversed(d["versiones"])}
    v = versions[c2.selectbox("Versión", list(versions), key=f"{key}_v")]
    if d["es_sintetico"]:
        st.warning("⚠️ Este dataset contiene datos **SINTÉTICOS**: no representan la situación real.")
    return {**v, "dataset": d}


def numeric_columns(version_id: int) -> list[str]:
    e = call(api().get, f"/datasets/versions/{version_id}/eda", quiet=True)
    return e["numericas"] if e else []
