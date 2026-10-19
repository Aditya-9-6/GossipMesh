# forced rebuild comment
# Multi‑stage build using official Python image
# Stage 1: Builder – install dependencies
FROM python:3.11-slim AS builder

# Set environment variables for pip
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies (for any compiled wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Create a non‑root user for later stage
RUN useradd -m -u 1000 appuser

# Copy project files
WORKDIR /app
COPY pyproject.toml poetry.lock* requirements.txt* ./
# Install dependencies (use pip for simplicity)
RUN pip install --upgrade pip && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; else echo "No requirements.txt"; fi

# Copy the rest of the source code
COPY . .

# Stage 2: Runtime – minimal image
FROM python:3.11-slim AS runtime

# Copy non‑root user from builder
COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group

# Install runtime dependencies only (already installed in builder)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Set workdir and copy app files
WORKDIR /app
COPY --from=builder /app /app

# Switch to non‑root user
USER appuser

# Expose the FastAPI port (default 8000)
EXPOSE 8000

# Use Uvicorn to serve the FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
