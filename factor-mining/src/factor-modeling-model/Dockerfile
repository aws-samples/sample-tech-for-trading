FROM python:3.9-slim

WORKDIR /app

# Copy requirements file first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run when the container starts
CMD ["python", "run_factor_analysis.py"]