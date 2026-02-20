# Dockerfile for MySecretary - Render Deployment
FROM python:3.11-slim

WORKDIR /app

# Install build dependencies for pymssql
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    gcc \
    make \
    freetds-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/'); print('healthy')"

# Run Flask app with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
