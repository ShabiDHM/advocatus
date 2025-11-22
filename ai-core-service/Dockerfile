# ai-core-service/Dockerfile
# FINAL PRODUCTION VERSION - FIXED SPACY URL

# Use a lightweight Python base
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# CRITICAL FIX: Direct download of the Spacy NER model (Version 3.7.0)
# We use the direct GitHub URL to bypass the broken 'spacy download' lookup
RUN pip install --no-cache-dir https://github.com/explosion/spacy-models/releases/download/xx_ent_wiki_sm-3.7.0/xx_ent_wiki_sm-3.7.0-py3-none-any.whl

# Copy the rest of the application code
COPY . .

# Expose the port
EXPOSE 8000

# Command to run the unified service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]