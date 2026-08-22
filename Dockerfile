# Multi-stage Docker build for FinExplain

# Stage 1: Build Frontend assets
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Backend runtime environment
FROM python:3.10-slim AS backend-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONUTF8=1 \
    USE_TF=0 \
    USE_TORCH=1 \
    ENVIRONMENT=production

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Backend application code
COPY backend/ /app/backend/
COPY sample_loan_details.pdf /app/

# Copy built frontend assets to the static directory expected by FastAPI
COPY --from=frontend-builder /frontend/dist /app/frontend/dist
COPY frontend/console.html /app/frontend/console.html

WORKDIR /app/backend

EXPOSE 8000

# Health check using the newly implemented /health/live endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
