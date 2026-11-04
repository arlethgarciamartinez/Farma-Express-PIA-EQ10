FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install -e ".[dev]"
COPY datos ./datos
COPY tests ./tests

# --- imagen de la aplicación (usuario sin privilegios) ---
FROM base AS app
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "--factory", "farmaexpress.api.main:crear_app", "--host", "0.0.0.0", "--port", "8000"]

# --- imagen de pruebas ---
FROM base AS tests
CMD ["pytest"]
