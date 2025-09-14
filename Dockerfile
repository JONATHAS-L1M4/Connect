FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Dependências que ajudam em wheels nativos (opcional, mas leve)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requisitos primeiro (cache de build)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Código
COPY . .

# Usuário não-root (opcional)
RUN useradd -ms /bin/bash appuser
USER appuser

# As portas expostas aqui são informativas; o Nginx acessa via rede interna
EXPOSE 8501 8502

# O comando é definido por serviço no docker-compose