# FILE: backend/Dockerfile
# PHOENIX PROTOCOL - INFRASTRUCTURE V4.0 (ALBANIAN VISION)
# 1. FIX: Added 'tesseract-ocr-sqi' to enable Albanian OCR.
# 2. RESULT: The system can now correctly read "ë" and "ç".

FROM python:3.11

# 1. Install system dependencies
# PHOENIX FIX: Added 'tesseract-ocr-sqi' (Albanian Language Pack)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-sqi \
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