# FILE: backend/Dockerfile
# PHOENIX PROTOCOL CURE 50.1 (COMPLETE BUILD MANIFEST):
# 1. ADDED SCRIPTS: A 'COPY ./scripts ./scripts' command has been added.
# 2. This ensures that the 'scripts' directory is included in the Docker image,
#    making the utility scripts available for execution within the container and
#    resolving the 'No such file or directory' error.

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

# 6. Copy the application source code AND utility scripts.
COPY ./app ./app
COPY ./scripts ./scripts

# 7. Expose the port that the Uvicorn server will run on.
EXPOSE 8000