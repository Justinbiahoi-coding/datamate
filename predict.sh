#!/bin/bash
# DataMate ZAC 2026 — Docker entrypoint.
# BTC mount:  /data  (read-only, split root)   /result  (writable)
set -e

mkdir -p /result/logs

echo "[PREDICT] start $(date -Iseconds)"
echo "[PREDICT] /data contents: $(ls /data 2>&1 | tr '\n' ' ')"

python3 /app/code/inference.py \
  --data-root /data \
  --out /result/submission.jsonl \
  --logs /result/logs \
  --model /app/models/qwen-datamate \
  2>&1 | tee -a /result/logs/run.log

echo "[PREDICT] done $(date -Iseconds).  $(wc -l < /result/submission.jsonl) câu."
