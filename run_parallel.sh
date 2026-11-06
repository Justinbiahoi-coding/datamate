#!/bin/bash
# Chạy 5 batch song song, merge, score
# Usage: ANTHROPIC_API_KEY=xxx ./run_parallel.sh [train|public_test]

set -e
SPLIT="${1:-train}"
BACKEND="${DATAMATE_LLM_BACKEND:-anthropic}"
N_TOTAL=3000
N_BATCH=5
PER_BATCH=$((N_TOTAL / N_BATCH))

echo "=== Chạy $N_BATCH batch song song, $PER_BATCH câu/batch ($BACKEND) ==="

for i in $(seq 0 $((N_BATCH-1))); do
  OFFSET=$((i * PER_BATCH))
  LIMIT=$PER_BATCH
  if [ $i -eq $((N_BATCH-1)) ]; then
    LIMIT=$((N_TOTAL - OFFSET))  # batch cuối lấy hết
  fi
  python3 code/agent.py \
    --split "$SPLIT" \
    --offset "$OFFSET" \
    --limit "$LIMIT" \
    --out "sub_$i.jsonl" > "log_$i.log" 2>&1 &
  echo "Batch $i (câu $OFFSET-$((OFFSET+LIMIT-1))): PID $!"
done

echo ""
echo "Đợi tất cả batch xong..."
wait

echo ""
echo "=== Merge ==="
cat sub_*.jsonl > submission_full.jsonl
echo "Tổng: $(wc -l < submission_full.jsonl) câu"

if [ "$SPLIT" = "train" ]; then
  echo ""
  echo "=== Score ==="
  python3 code/scorer.py --split train --sub submission_full.jsonl
fi
