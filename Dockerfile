# ============================================================
# Integra Neural Engine — Dockerfile
# Backend only: FastAPI + AI/CV stack (No Frontend)
# ============================================================

# --- Base Image ---
FROM python:3.11-slim

# --- Environment Variables ---
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
ENV HF_HOME=/root/.cache/huggingface
ENV TORCH_HOME=/root/.cache/torch
ENV PIP_DEFAULT_TIMEOUT=300
ENV PIP_RETRIES=10

# --- System Dependencies ---
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# --- Working Directory ---
WORKDIR /app

# --- Copy Requirements File ---
COPY requirements.txt .

# --- Step 1: Base pip + protobuf (prevents MediaPipe conflicts) ---
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir protobuf==4.25.8

# --- Step 2: Pre-install PyTorch CPU-only (no GPU on this server!) ---
# CPU build = ~200MB instead of 1.3GB (saves NVIDIA CUDA libraries)
RUN pip install --no-cache-dir --timeout 300 --retries 10 \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

# OpenCV (~150MB) — separate layer for same reason
RUN pip install --no-cache-dir --timeout 300 --retries 10 \
    "opencv-contrib-python>=4.10.0"

# --- Step 3: Install the rest from requirements.txt ---
# pip will skip torch & opencv since they're already installed above
RUN pip install --no-cache-dir --timeout 300 --retries 10 -r requirements.txt

# --- Step 4: Download Spacy NLP Model ---
RUN python -m spacy download en_core_web_sm

# --- Step 5: Cleanup build tools (not needed at runtime) ---
# Removes GCC, G++, make, etc. — saves ~600MB from final image
RUN apt-get purge -y --auto-remove \
    build-essential \
    libxrender-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /root/.cache/pip

# --- Copy Backend Source Code ---
COPY backend/ ./backend/
COPY tracker.py .

# --- Expose API Port ---
EXPOSE 8000

# --- Health Check ---
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# --- Run Server ---
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
