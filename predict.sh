#!/bin/bash
# Entrypoint cho Docker submission
# BTC mount /data (read-only) và /result (writable)
set -e

mkdir -p /result/logs

python3 /app/code/agent.py \
  --split "${SPLIT:-public_test}" \
  --data-dir /data \
  --out /result/submission.jsonl \
  2>&1 | tee /result/logs/run.log

echo "Done. $(wc -l < /result/submission.jsonl) câu đã ghi."
