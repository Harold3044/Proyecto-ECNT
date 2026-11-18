# Imagen única para los tres servicios (API, App Administrador, App EPS); cada servicio cambia el comando.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencias con versiones exactas (reproducibilidad)
COPY requirements.lock.txt ./
RUN pip install -r requirements.lock.txt

# Código. Instalación editable para que las rutas del proyecto (data/) se resuelvan desde /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY apps ./apps
COPY scripts ./scripts
RUN pip install --no-deps -e .

# Usuario sin privilegios; data/ se monta como volumen
RUN useradd --create-home --uid 1000 ecnt && mkdir -p /app/data/storage && chown -R ecnt /app/data
USER ecnt

EXPOSE 8000 8501 8502
CMD ["uvicorn", "ecnt_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
