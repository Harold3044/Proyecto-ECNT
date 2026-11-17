# Datos

Los archivos de datos **no se versionan**. Para regenerarlos:

1. Coloque en `data/raw/` el anexo NBI `CNPV-2018-NBI-DIVIPOLA-2021.xlsx` (DANE).
2. Descargue a `data/raw/dane_proyecciones/` y `data/raw/dane_eevv/` los archivos indicados en `docs/datos/FUENTE_*.md`.
3. Ejecute `python scripts/construir_dataset_caribe.py`.

| Carpeta | Contenido |
|---|---|
| `raw/` | Fuentes oficiales tal como se descargaron (nunca se modifican) |
| `interim/` | Copias intermedias (p. ej. cuadros DANE desprotegidos) |
| `processed/` | Datasets listos: `caribe_modelado.csv`, `caribe_panel_municipio_anio.csv`, `manifiesto.json` |
| `synthetic/` | Datos **sintéticos** para pruebas (prefijo `SINTETICO_`) |
| `storage/` | Almacén de la API (base de datos, versiones, modelos) |
