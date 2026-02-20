#!/bin/bash
set -e

echo "=== Installing system dependencies for ODBC and pyodbc ==="

# Update package manager
apt-get update

# Install build essentials and ODBC dependencies
apt-get install -y \
    g++ \
    gcc \
    make \
    unixodbc-dev \
    libltdl-dev \
    wget

# Install ODBC Driver 18 for SQL Server
echo "=== Installing ODBC Driver 18 for SQL Server ==="

# Add Microsoft package repository
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Update and install ODBC driver
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql18

echo "=== ODBC Driver installed successfully ==="

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Build completed successfully ==="
