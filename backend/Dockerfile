# FILE: backend/Dockerfile
# PHOENIX PROTOCOL - ULTIMATE DIAGNOSTIC

FROM python:3.11

# 1. Install system dependencies.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libreoffice \
    dnsutils \
    iputils-ping \
    curl && \
    rm -rf /var/lib/apt/lists/*

# 2. Verify installations.
RUN tesseract --version
RUN soffice --version

# 3. Set working directory and PYTHONPATH.
WORKDIR /app
ENV PYTHONPATH /app

# 4. Copy requirements file.
COPY requirements.txt .

# 5. Install Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# 6. ULTIMATE VERIFICATION:
#    Print the exact versions of all installed packages to the build log.
#    This will provide irrefutable evidence of the installed uvicorn version.
RUN pip freeze

# 7. Copy application source code.
COPY ./app ./app
COPY ./scripts ./scripts

# 8. Expose the port.
EXPOSE 8000