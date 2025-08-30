# Use Python 3.11 as base image (better compatibility with backtrader)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Docker-specific requirements first for better caching
COPY docker/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire src directory
COPY src/ ./src/

# Copy environment template
COPY .env .env

# Set Python path to include src directory
ENV PYTHONPATH=/app/src:/app:$PYTHONPATH

# Create directories for outputs
RUN mkdir -p /app/backtest_results /app/logs

# Set default command to run backtest job
CMD ["python", "src/batch_jobs/backtest_job.py"]
