# FILE: backend/Dockerfile
# PHOENIX PROTOCOL - INFRASTRUCTURE V4.1 (MULTILANGUAGE OCR)
# 1. ADDED: Multiple language packs for better invoice recognition
# 2. RESULT: OCR works with receipts in English, German, French, Italian, Spanish

FROM python:3.11

# 1. Install system dependencies
# PHOENIX ENHANCEMENT: Added multiple language packs for invoices
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-sqi \
    tesseract-ocr-eng \
    tesseract-ocr-deu \
    tesseract-ocr-fra \
    tesseract-ocr-ita \
    tesseract-ocr-spa \
    libreoffice \
    dnsutils \
    iputils-ping \
    curl && \
    rm -rf /var/lib/apt/lists/*

# 2. Verify Tesseract and LibreOffice installations.
RUN tesseract --version
RUN soffice --version

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