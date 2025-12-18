# Use slim Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (Docker caching)
COPY requirements.txt .

# Install Python dependencies
RUN python -m pip install --upgrade pip
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Environment variables
ENV PORT=8080
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8080

# Start the app using Gunicorn + Uvicorn worker
CMD ["gunicorn", "--bind", ":8080", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--threads", "8", "--timeout", "0", "src.main:app"]
