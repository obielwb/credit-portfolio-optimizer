FROM python:3.11-slim-bookworm

# Image shared by the backend API and worker services in Docker Compose.

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        "sqlalchemy>=2.0" \
        "psycopg2-binary>=2.9" \
        "uvicorn>=0.22" \
        "fastapi>=0.100" \
        "pydantic>=2.5" \
        "python-dotenv>=1.0" \
        "pandas>=2.0" \
        "pyarrow>=15.0" \
        "python-multipart>=0.0.6" \
        "numpy>=1.26" \
        "httpx>=0.24" \
        "minio>=7.2" \
        "aio-pika>=9.4" \
        "ortools>=9.10" \
        "scikit-learn>=1.3"

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8000
