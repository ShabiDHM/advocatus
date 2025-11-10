# FILE: backend/Dockerfile
# PHOENIX PROTOCOL CURE 49.2 (OPTIMIZED BUILD PROCESS):
# 1. Split COPY commands to properly leverage Docker's build cache. Dependency
#    installation is now separate from source code copying.
# 2. This ensures source code changes ALWAYS result in a fresh application
#    layer, while dependencies are only re-installed if requirements.txt changes.

FROM python:3.11

# 1. Install system dependencies.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    dnsutils \
    iputils-ping \
    curl && \
    rm -rf /var/lib/apt/lists/*

# 2. Verify Tesseract installation.
RUN tesseract --version

# 3. Set the working directory and PYTHONPATH.
WORKDIR /app
ENV PYTHONPATH /app

# 4. Copy ONLY the requirements file first to leverage Docker cache.
COPY requirements.txt .

# 5. Install Python dependencies. This step will only re-run if requirements.txt changes.
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the application source code. This will be a fresh copy on every code change.
COPY ./app ./app

# 7. Expose the port that the Uvicorn server will run on.
EXPOSE 8000