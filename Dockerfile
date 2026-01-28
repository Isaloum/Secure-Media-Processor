# Secure Media Processor - CPU Version
# Multi-stage build for smaller final image

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install optional medical imaging dependencies
RUN pip install --no-cache-dir pydicom nibabel scipy scikit-image || true

# ============================================================================
# Stage 2: Runtime
# ============================================================================
FROM python:3.11-slim as runtime

# Security: Create non-root user
RUN groupadd -r smp && useradd -r -g smp smp

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=smp:smp src/ ./src/
COPY --chown=smp:smp main.py .
COPY --chown=smp:smp scripts/ ./scripts/

# Create directories with secure permissions
RUN mkdir -p /app/keys /app/media_storage /app/temp && \
    chown -R smp:smp /app && \
    chmod 700 /app/keys /app/temp

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GPU_ENABLED=false \
    TEMP_PATH=/app/temp \
    LOCAL_STORAGE_PATH=/app/media_storage \
    MASTER_KEY_PATH=/app/keys/master.key

# Switch to non-root user
USER smp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.encryption import MediaEncryptor; print('OK')" || exit 1

# Default command: show help
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
