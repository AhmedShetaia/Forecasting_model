# Use a specific Python version to ensure compatibility
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies and uv for faster package installation
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

# Add uv to PATH
ENV PATH="/root/.cargo/bin:$PATH"

# Copy requirements and install dependencies using uv
COPY requirements.txt .
RUN uv pip install --system --no-cache --upgrade pip setuptools wheel
RUN uv pip install --system --no-cache -r requirements.txt

# Copy the application code
COPY . .

# Copy selective symlink initialization script
COPY scripts/init_data_symlinks.sh /usr/local/bin/init_data_symlinks.sh
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
