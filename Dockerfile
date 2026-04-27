# Use Python 3.11 slim as base
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g repomix \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
# We don't have a requirements.txt yet, so we'll install directly or create one
COPY manage_projects.py Makefile server.py ./
COPY web/ ./web/

RUN pip install --no-cache-dir pyyaml click fastapi uvicorn pydantic

# Create necessary directories
RUN mkdir -p projects archive repos

# Expose the port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the server
CMD ["python", "server.py"]
