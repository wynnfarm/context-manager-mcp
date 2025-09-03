# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV CONTEXT_STORAGE_PATH=/app/contexts

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create contexts directory
RUN mkdir -p /app/contexts

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash context_user && \
    chown -R context_user:context_user /app

# Switch to non-root user
USER context_user

# Expose port for REST API
EXPOSE 8000

# Set the default command to run the working JSON-RPC server
CMD ["python", "context_manager_jsonrpc_server.py"]
