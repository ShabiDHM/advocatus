# FILE: backend/Dockerfile
# PHOENIX PROTOCOL - FINAL ERADICATION OF CORRUPTED STATE

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

# 5. THE ERADICATION STEP:
#    Forcefully uninstall any pre-existing or 'phantom' version of Uvicorn
#    that may be present in the base image. This purifies the environment
#    before we install our known-good dependencies.
RUN pip uninstall -y uvicorn

# 6. Install our specified Python dependencies into the now-clean environment.
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copy application source code.
COPY ./app ./app
COPY ./scripts ./scripts

# 8. Expose the port.
EXPOSE 8000