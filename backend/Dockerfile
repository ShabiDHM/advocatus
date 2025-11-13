# FILE: backend/Dockerfile

FROM python:3.11

# 1. Install system dependencies, now including LibreOffice for document conversion.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
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

# 5. Install Python dependencies. This step will only re-run if requirements.txt changes.
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the application source code AND utility scripts.
COPY ./app ./app
COPY ./scripts ./scripts

# 7. Expose the port that the Uvicorn server will run on.
EXPOSE 8000