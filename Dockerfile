FROM vllm/vllm-openai:v0.10.1.1

# Cấu hình môi trường offline hoàn toàn
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    PIP_NO_CACHE_DIR=1 \
    NCCL_P2P_DISABLE=1

WORKDIR /code

# Cài đặt các thư viện cần thiết
COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt
RUN pip install --no-cache-dir --no-deps nvidia-nccl-cu12==2.27.7

# Copy toàn bộ mã nguồn, weights model và thư mục training code vào image
COPY models/ /code/models/
COPY src/ /code/src/
COPY training_code/ /code/training_code/
COPY predict.sh README.md /code/

RUN chmod +x /code/predict.sh

ENTRYPOINT ["bash", "/code/predict.sh"]