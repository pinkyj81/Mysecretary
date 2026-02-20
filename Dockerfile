# Dockerfile for MySecretary - Render Deployment
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for ODBC
RUN apt-get update && apt-get install -y \
    g++ \
    gcc \
    make \
    unixodbc-dev \
    libltdl-dev \
    curl \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# Add Microsoft package repository and install ODBC Driver 18
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 5000

# Run Flask app with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "60", "app:app"]
