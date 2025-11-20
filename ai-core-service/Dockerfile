# Use a lightweight Python base
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for some AI libraries)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download the specific Albanian Spacy model (if we use it later, ensuring it's ready)
# RUN python -m spacy download sq_core_news_sm || true

# Copy the rest of the application code
COPY . .

# Expose the port
EXPOSE 8000

# Command to run the unified service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]