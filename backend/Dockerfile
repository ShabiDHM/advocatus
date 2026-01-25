# FILE: backend/Dockerfile
# PHOENIX PROTOCOL - INFRASTRUCTURE V4.2 (KOSOVO MARKET OPTIMIZED)
# 1. PRIORITY: Albanian language first (sqi)
# 2. SUPPORT: English and German for international receipts
# 3. MINIMAL: Only essential language packs for Kosovo market

FROM python:3.11

# 1. Install system dependencies OPTIMIZED FOR KOSOVO MARKET
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # CORE OCR (Kosovo priority)
    tesseract-ocr \
    tesseract-ocr-sqi \        # ALBANIAN - PRIMARY
    tesseract-ocr-eng \        # English - for international receipts
    tesseract-ocr-deu \        # German - common in Kosovo business
    # Business tools
    libreoffice \
    # System utilities
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