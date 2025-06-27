# Use a specific Python version to ensure compatibility
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Ensure directories exist for Azure File Share mount points
RUN mkdir -p /app/scraping/scraped_data \
    /app/modelling/predictions \
    /app/modelling/cache \
    /app/forecasting/data

# Default command to run the pipeline
ENTRYPOINT ["python", "run_pipeline.py"]

# Default arguments (can be overriden with docker run)
CMD []
