# ==============================================================================
# GossipMesh Enterprise Air-Gapped AI Reviewer
# Multi-Stage Dockerfile with Parameter-Tiered Model Bundles
# ==============================================================================
# Supported Bundle Arguments:
#   BUNDLE_ID=b01  -> Qwen2.5-Coder 1.5B (Syntax & Lint Specialist, $10K/yr)
#   BUNDLE_ID=b02  -> Gemma-2-2B / Qwen 3B (Medium Static Analysis, $15K/yr)
#   BUNDLE_ID=b03  -> Qwen2.5-Coder 7B (Full-Code Review, $25K/yr)
#   BUNDLE_ID=b04  -> Qwen2.5-Coder 14B (Flagship Enterprise Architecture, $50K/yr) [DEFAULT]
#   BUNDLE_ID=b05  -> Qwen2.5-Coder 32B (Deep Auto-Remediation / Defense, $75K/yr)
# ==============================================================================

ARG BUNDLE_ID=b04

# Stage 1: Base Runtime Environment
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    AIR_GAPPED=1

# Create non-privileged service user for defense/enterprise security compliance
RUN groupadd -g 1000 reviewer && \
    useradd -u 1000 -g reviewer -m -s /bin/bash reviewer

WORKDIR /app

# Install enterprise dependencies
COPY enterprise/requirements.txt /app/enterprise/requirements.txt
RUN python -m pip install --upgrade --no-cache-dir pip && \
    python -m pip install --no-cache-dir -r /app/enterprise/requirements.txt

# Copy core engine, scripts, and embedded RSA-4096 public key
COPY enterprise/ /app/enterprise/
COPY scripts/infrastructure_reviewer.py /app/scripts/infrastructure_reviewer.py

# Stage 2: Final Bundle-Specific Air-Gapped Image
FROM base AS final
ARG BUNDLE_ID

# Copy designated model bundle weights and configuration
COPY models/${BUNDLE_ID}*/ /app/models/${BUNDLE_ID}/

# Set non-root user permissions
RUN chown -R reviewer:reviewer /app

USER reviewer
WORKDIR /workspace

# Container entry point runs the cryptographic packaging CLI
ENTRYPOINT ["python", "-m", "enterprise.packaging"]
CMD ["--repo-path", "/workspace"]
