# Use a specific Python version to ensure compatibility
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for potential compilation needs (least changing)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies (changes occasionally)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy scripts first (changes less frequently than main code)
COPY scripts/init_data_symlinks.sh /usr/local/bin/init_data_symlinks.sh

# Copy the application code (most frequently changing - placed last)
COPY . .

# Make scripts executable
RUN chmod +x /usr/local/bin/init_data_symlinks.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Create entrypoint script that initializes symlinks before running pipeline
COPY <<EOF /usr/local/bin/entrypoint.sh
#!/bin/bash
set -e

echo "Initializing selective data symlinks..."
/usr/local/bin/init_data_symlinks.sh

echo "Starting pipeline..."
exec python run_pipeline.py "\$@"
EOF

RUN chmod +x /usr/local/bin/entrypoint.sh

# Use custom entrypoint that sets up symlinks
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default arguments (can be overriden with docker run)
CMD ["--log-level", "INFO"]
