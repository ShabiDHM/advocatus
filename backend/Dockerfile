# FILE: backend/Dockerfile
# PHOENIX PROTOCOL - INFRASTRUCTURE V4.2 (KOSOVO MARKET OPTIMIZED)
# FIXED: Correct Dockerfile line continuation syntax

FROM python:3.11

# 1. Install system dependencies OPTIMIZED FOR KOSOVO MARKET
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-sqi \
    tesseract-ocr-eng \
    tesseract-ocr-deu \
    libreoffice \
    dnsutils \
    iputils-ping \
    curl && \
    rm -rf /var/lib/apt/lists/*

# 2. Verify Albanian OCR specifically
RUN echo "Testing Albanian OCR support..." && \
    tesseract --list-langs | grep -q sqi && echo "✅ Albanian (sqi) support confirmed" || echo "⚠️  Albanian support missing"

# 3. Set the working directory and PYTHONPATH.
WORKDIR /app
ENV PYTHONPATH /app

# 4. Copy ONLY the requirements file first to leverage Docker cache.
COPY requirements.txt .

# 5. Install Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the application source code AND utility scripts.
COPY ./app ./app
COPY ./scripts ./scripts

# 7. Expose the port.
EXPOSE 8000