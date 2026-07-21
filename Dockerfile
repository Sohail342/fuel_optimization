FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for GeoDjango + PostGIS
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    binutils \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

# Install dependencies from lock file
RUN uv sync --frozen

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]