# Datos

Los archivos de datos **no se versionan**. Para regenerarlos:

1. Coloque en `data/raw/` el anexo NBI `CNPV-2018-NBI-DIVIPOLA-2021.xlsx` (DANE).
2. Descargue a `data/raw/dane_proyecciones/` y `data/raw/dane_eevv/` los archivos indicados en `docs/datos/FUENTE_*.md`.
3. Ejecute `python scripts/construir_dataset_caribe.py`.
4. (Mapa) Descargue las coordenadas DIVIPOLA de las cabeceras municipales (DANE, publicadas en datos.gov.co):
   `curl -L -o data/external/divipola/divipola_municipios.json "https://www.datos.gov.co/resource/gdxc-w37w.json?$limit=5000"`
   Sin este archivo la plataforma funciona, pero el ambiente EPS no muestra el mapa.

| Carpeta | Contenido |
|---|---|
| `raw/` | Fuentes oficiales tal como se descargaron (nunca se modifican) |
| `interim/` | Copias intermedias (p. ej. cuadros DANE desprotegidos) |
| `processed/` | Datasets listos: `caribe_modelado.csv`, `caribe_panel_municipio_anio.csv`, `manifiesto.json` |
| `synthetic/` | Datos **sintéticos** para pruebas (prefijo `SINTETICO_`) |
| `storage/` | Almacén de la API (base de datos, versiones, modelos) |
