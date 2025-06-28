# Use a specific Python version to ensure compatibility
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for potential compilation needs
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Ensure directories exist for data and outputs
RUN mkdir -p /app/scraping/scraped_data \
    /app/modelling/predictions \
    /app/modelling/cache \
    /app/forecasting/data \
    /app/logs

# Create a non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Default command to run the pipeline
ENTRYPOINT ["python", "run_pipeline.py"]

# Default arguments (can be overriden with docker run)
CMD ["--log-level", "INFO"]
