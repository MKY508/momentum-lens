# Multi-stage build for Python FastAPI backend
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_ENV=production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for TA-Lib and other native packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    libta-dev \
    pkg-config \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib from source (required for ta-lib Python package)
RUN cd /tmp \
    && wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib/ \
    && ./configure --prefix=/usr \
    && make \
    && make install \
    && cd / \
    && rm -rf /tmp/ta-lib*

# Create and use non-root user
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Set work directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/home/appuser/.local/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    libta-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy TA-Lib library from builder
COPY --from=builder /usr/lib/libta_lib.* /usr/lib/
COPY --from=builder /usr/include/ta-lib/ /usr/include/ta-lib/

# Create non-root user
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Set work directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# Development stage (optional)
FROM production as development

# Switch back to root to install dev dependencies
USER root

# Install development tools
RUN apt-get update && apt-get install -y \
    git \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install --no-cache-dir \
    debugpy \
    ipython \
    jupyter

# Switch back to appuser
USER appuser

# Run with auto-reload for development
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]