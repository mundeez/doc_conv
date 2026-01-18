# Base image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps (pandoc for conversions, docker client for wrapper)
RUN apt-get update \
    && apt-get install -y --no-install-recommends pandoc docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Ensure wrapper is executable (for PANDOC_BIN)
RUN chmod +x scripts/pandoc_docker.sh

EXPOSE 8000

# Default command: migrate then runserver
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
