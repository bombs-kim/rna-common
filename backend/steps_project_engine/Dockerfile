# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
# PYTHONUNBUFFERED: Prevents Python from buffering stdout/stderr
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files
# PIP_NO_CACHE_DIR: Disables pip cache to reduce image size
# PIP_DISABLE_PIP_VERSION_CHECK: Disables pip version check warnings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
# curl: Required for downloading Cursor CLI installation script
# git: Required for version control operations
# bash: Shell environment
# Remove apt lists to reduce image size (saves ~50-100MB)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Install Cursor CLI for appuser
USER appuser
# Install Cursor CLI (the script installs to ~/.local/bin/cursor-agent)
RUN curl https://cursor.com/install -fsS | bash

# Add ~/.local/bin to PATH (as the install script suggests)
ENV PATH="/home/appuser/.local/bin:${PATH}"

WORKDIR /app

# Keep container running
CMD ["tail", "-f", "/dev/null"]
