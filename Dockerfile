# Dockerfile for trix-hub
# Optimized for ARM64/aarch64 (Raspberry Pi 5)
# Built on Windows PC with Docker Desktop + ARM64 emulation

# Use official Python slim image (supports ARM64)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Pillow (image processing)
# - libjpeg-dev, zlib1g-dev: JPEG support
# - libfreetype6-dev: Font rendering support
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first (better layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy fonts
COPY fonts/ /app/fonts/

# Copy trixhub package
COPY trixhub/ /app/trixhub/

# Copy application code
COPY app.py .

# Create non-root user for security
RUN useradd -m -u 1000 trixhub && \
    chown -R trixhub:trixhub /app

# Add /app to PYTHONPATH so trixhub package can be imported
ENV PYTHONPATH=/app

# Switch to non-root user
USER trixhub

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Health check (optional, useful for production)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "print('healthy')" || exit 1

# Run the application
CMD ["python", "app.py"]
