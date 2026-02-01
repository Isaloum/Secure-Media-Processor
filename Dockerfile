# Secure Media Processor - CPU Version
# Multi-stage build for optimized production images
# Supports secure data pipeline for cloud-to-GPU transfers

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

# Copy package files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install package with medical and azure extras
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir ".[medical,azure]"

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
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=smp:smp src/ ./src/
COPY --chown=smp:smp pyproject.toml README.md ./
COPY --chown=smp:smp docs/ ./docs/
COPY --chown=smp:smp plugins/ ./plugins/

# Create directories with secure permissions
RUN mkdir -p /app/keys /app/data/input /app/data/output /app/data/temp && \
    chown -R smp:smp /app && \
    chmod 700 /app/keys /app/data/temp

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GPU_ENABLED=false \
    SMP_INPUT_DIR=/app/data/input \
    SMP_OUTPUT_DIR=/app/data/output \
    SMP_TEMP_DIR=/app/data/temp \
    SMP_KEYS_DIR=/app/keys

# Switch to non-root user
USER smp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.core import SecureTransferPipeline; print('OK')" || exit 1

# Use the installed CLI entry point
ENTRYPOINT ["smp"]
CMD ["--help"]
