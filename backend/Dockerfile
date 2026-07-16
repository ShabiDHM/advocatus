# PHOENIX PROTOCOL - PRODUCTION CLOUD INFRASTRUCTURE V5.0
# Optimized for: Render Free Tier (512MB RAM)
# Target: Python 3.13 / FastAPI

FROM python:3.13-slim

# 1. Install critical system dependencies (Lightweight)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-sqi \
    curl && \
    rm -rf /var/lib/apt/lists/*

# 2. Set working environment
WORKDIR /app
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 3. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 4. Copy Application Code
COPY ./app ./app

# 5. Start Command
# Using 1 worker and no-reload for maximum RAM efficiency on Free Tier
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]