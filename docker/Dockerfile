# GENESIS Docker Image
# Multi-stage build for optimized image size

# ============================================
# Stage 1: Base image with system dependencies
# ============================================
FROM nvidia/cuda:12.1.0-devel-ubuntu22.04 AS base

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-dev \
    python3-pip \
    git \
    git-lfs \
    curl \
    wget \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 \
    && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# ============================================
# Stage 2: Build stage
# ============================================
FROM base AS builder

# Set working directory
WORKDIR /build

# Copy dependency files
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cu121 \
    && pip install --no-cache-dir numpy scipy matplotlib

# ============================================
# Stage 3: Runtime image
# ============================================
FROM base AS runtime

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . /app/

# Install the package
RUN pip install --no-cache-dir -e .

# Create necessary directories
RUN mkdir -p /app/logs /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0
ENV GENESIS_CONFIG_DIR=/app/configs

# Expose port for Dashboard (if needed)
EXPOSE 8501

# Default command
CMD ["python", "scripts/run_genesis.py", "--goal", "assembled_robot"]

# ============================================
# Usage:
# 
# Build:
#   docker build -t genesis:latest -f docker/Dockerfile .
#
# Run with GPU:
#   docker run --gpus all -it genesis:latest
#
# Run specific test:
#   docker run --gpus all genesis:latest python scripts/test_skills.py --test all
#
# Interactive shell:
#   docker run --gpus all -it genesis:latest /bin/bash
# ============================================
