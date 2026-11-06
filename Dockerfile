# DataMate ZAC 2026 — Docker image để nộp bài
# Target: 2× RTX 5090 (CUDA 12.8), chạy fully offline

FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

# Python + hệ thống
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt

# Code + model weights (weights điền sau khi fine-tune xong)
COPY code/ /app/code/
COPY predict.sh /app/
COPY models/ /app/models/

RUN chmod +x /app/predict.sh

# Offline inference backend
ENV DATAMATE_LLM_BACKEND=local \
    LOCAL_MODEL_PATH=/app/models/qwen3-8b-datamate

ENTRYPOINT ["/app/predict.sh"]
