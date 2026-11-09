# DataMate ZAC 2026 — Docker image để nộp bài.
# Target: 2× RTX 5090 (CUDA 12.8), chạy fully offline (HF_HUB_OFFLINE=1).

FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_DATASETS_OFFLINE=1 \
    TOKENIZERS_PARALLELISM=false \
    DATAMATE_LLM_BACKEND=local

# Python 3.11 + system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3.11 python3-pip python3.11-venv \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

WORKDIR /app

# Python deps
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt

# Code
COPY code/ /app/code/
COPY predict.sh /app/
RUN chmod +x /app/predict.sh

# Model weights (merged base + LoRA). Phải build sau khi fine-tune xong.
# Để build CI test không fail khi chưa có weights:
#   mkdir -p models/qwen-datamate && touch models/qwen-datamate/.placeholder
COPY models/ /app/models/

ENTRYPOINT ["/app/predict.sh"]
