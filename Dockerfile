# Dockerfile for Self-Refine CLI Worker
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    python3-dev \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for cache efficiency
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create sandbox directory
RUN mkdir -p sandbox

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV IN_DOCKER_CONTAINER=true

# Default command (will be overridden by docker-compose or agent)
CMD ["python", "autonomous_loop.py"]
