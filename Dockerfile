# Dockerfile for PalletDataGenerator development
# Multi-stage build for optimized development and production images

# Base stage with Python and system dependencies
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libxt6 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash pallet
WORKDIR /home/pallet/app
RUN chown pallet:pallet /home/pallet/app

# Switch to non-root user
USER pallet

# Add local bin to PATH
ENV PATH="/home/pallet/.local/bin:$PATH"

# Development stage
FROM base as development

# Copy requirements first for better caching
COPY --chown=pallet:pallet requirements*.txt ./
RUN pip install --user -r requirements-dev.txt

# Copy source code
COPY --chown=pallet:pallet . .

# Install package in development mode
RUN pip install --user -e .

# Install pre-commit hooks
RUN pre-commit install || true

EXPOSE 8000
CMD ["bash"]

# Production stage
FROM base as production

# Copy requirements
COPY --chown=pallet:pallet requirements.txt ./
RUN pip install --user -r requirements.txt

# Copy source code
COPY --chown=pallet:pallet src/ ./src/
COPY --chown=pallet:pallet pyproject.toml README.md ./

# Install package
RUN pip install --user .

# Set entrypoint
ENTRYPOINT ["palletgen"]
CMD ["--help"]

# Blender integration stage (for Blender-based development)
FROM base as blender

# Install Blender (latest LTS version)
ENV BLENDER_VERSION=4.0
ENV BLENDER_URL=https://download.blender.org/release/Blender4.0/blender-4.0.2-linux-x64.tar.xz

RUN wget -q $BLENDER_URL -O blender.tar.xz \
    && tar -xf blender.tar.xz \
    && rm blender.tar.xz \
    && mv blender-* blender

# Add Blender to PATH
ENV PATH="/home/pallet/app/blender:$PATH"

# Copy requirements and install
COPY --chown=pallet:pallet requirements*.txt ./
RUN pip install --user -r requirements-dev.txt

# Copy source code
COPY --chown=pallet:pallet . .

# Install package in development mode
RUN pip install --user -e .

# Create Blender Python symlink for better integration
RUN ln -sf /home/pallet/app/blender/4.0/python/bin/python3.11 /home/pallet/.local/bin/blender-python

EXPOSE 8000
CMD ["bash"]
