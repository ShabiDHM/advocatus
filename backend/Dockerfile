# backend/Dockerfile
# DEFINITIVE VERSION 8.0 (PHOENIX PROTOCOL: RUNTIME IMPORT FIX)
# 1. CRITICAL FIX: Added 'ENV PYTHONPATH /app' to explicitly set the Python
#    import path. This resolves the 'ModuleNotFoundError' on container startup
#    by telling the interpreter where to find the 'app' package.

FROM python:3.11

# 1. Install system dependencies.
RUN apt-get update && apt-get install -y tesseract-ocr && rm -rf /var/lib/apt/lists/*

# 2. Verify Tesseract installation.
RUN tesseract --version

# 3. Install network utilities.
RUN apt-get update && \
    apt-get install -y --no-install-recommends dnsutils iputils-ping curl && \
    rm -rf /var/lib/apt/lists/*

# 4. Set the working directory inside the container.
WORKDIR /app

# 5. --- PHOENIX PROTOCOL FIX: Set the PYTHONPATH ---
#    This tells the Python interpreter to look for packages in the /app directory,
#    allowing it to find the 'app' module at /app/app.
ENV PYTHONPATH /app

# 6. Copy and install Python dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copy the rest of the application's source code.
COPY . .

# 8. Expose the port that the Uvicorn server will run on.
EXPOSE 8000