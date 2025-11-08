# FILE: ai-service.Dockerfile (DEFINITIVE V17.0 - HEALTHCHECK FIX)
# This Dockerfile uses the single, unified requirements.txt from the backend service.
# FIX: Includes 'curl' for robust healthchecks.

FROM python:3.11-slim

WORKDIR /app

# --- Step 0: Install System Dependencies (curl for healthchecks) ---
# Update apt and install curl. Clean up apt cache to keep image size down.
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# --- Step 1: Install All Python Dependencies from the Single Source of Truth ---
# Copy the unified requirements.txt file from the backend directory.
COPY ./backend/requirements.txt ./requirements.txt

# Install all dependencies. This includes fastapi, spacy, torch, etc. for all services.
RUN pip install --no-cache-dir -r requirements.txt

# --- Step 2: Install and Cache AI Models ---
ENV HF_HOME=/huggingface_cache
ENV SENTENCE_TRANSFORMERS_HOME=/huggingface_cache
RUN pip install --no-cache-dir https://github.com/explosion/spacy-models/releases/download/xx_ent_wiki_sm-3.7.0/xx_ent_wiki_sm-3.7.0-py3-none-any.whl && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')" && \
    python -c "from transformers import pipeline; pipeline('zero-shot-classification', model='facebook/bart-large-mnli')"

# --- Step 3: Copy Application Code ---
# This build argument is still needed to copy the correct main.py.
ARG SERVICE_NAME
COPY ./${SERVICE_NAME}/. .

# --- Step 4: Expose Port and Run ---
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
