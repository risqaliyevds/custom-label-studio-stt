# Label Studio Audio Analysis Prediction API
# Multi-stage Docker build for production deployment

# Build arguments for cache busting (optional)
ARG CACHEBUST=1
ARG BUILD_DATE
ARG BUILD_VERSION=2.0.0

# Build stage
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /build

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Optional cache busting for requirements
RUN echo "Cache bust: ${CACHEBUST} at $(date)" && \
    echo "Build version: ${BUILD_VERSION}"

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH=/home/appuser/.local/bin:$PATH

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create directories
RUN mkdir -p /app /tmp/audio_analysis /var/log/app /home/appuser/.local && \
    chown -R appuser:appuser /app /tmp/audio_analysis /var/log/app /home/appuser

# Copy Python dependencies from builder stage to appuser's local directory
COPY --from=builder /root/.local /home/appuser/.local
RUN chown -R appuser:appuser /home/appuser/.local

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser app/ app/
COPY --chown=appuser:appuser main.py .
COPY --chown=appuser:appuser env.example .env.example

# Switch to non-root user
USER appuser

# Create startup script
COPY --chown=appuser:appuser <<EOF /app/start.sh
#!/bin/bash
set -e

# Print startup information
echo "Starting Label Studio Audio Analysis Prediction API v${VERSION:-2.0.0}"
echo "Environment: ${ENVIRONMENT:-production}"
echo "Host: ${HOST:-0.0.0.0}"
echo "Port: ${PORT:-9090}"

# Health check for required environment variables
if [ -z "\${GEMINI_API_KEY}" ]; then
    echo "Error: GEMINI_API_KEY environment variable is required"
    exit 1
fi

# Start the application
exec python main.py \\
    --host "${HOST:-0.0.0.0}" \\
    --port "${PORT:-9090}" \\
    --workers "${WORKERS:-1}" \\
    --log-level "${LOG_LEVEL:-info}"
EOF

RUN chmod +x /app/start.sh

# Expose port
EXPOSE 9090

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-9090}/health || exit 1

# Labels for metadata
LABEL maintainer="Audio Analysis Team" \
      version="2.0.0" \
      description="Label Studio Audio Analysis Prediction API" \
      org.opencontainers.image.title="Label Studio Audio Analysis API" \
      org.opencontainers.image.description="Robust ML backend for Label Studio with Gemini AI" \
      org.opencontainers.image.version="2.0.0" \
      org.opencontainers.image.vendor="Audio Analysis Team"

# Default command
CMD ["/app/start.sh"]
