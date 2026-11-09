# DataMate Pipeline — v2 (upgraded)

Nâng cấp dựa trên 15 techniques từ papers Text-to-SQL + code-gen SFT (BIRD, CodeS, DAIL-SQL, MAC-SQL).

## Quy trình đầy đủ

```
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│ 1. Gen data (×N)     │─→ │ 2. Merge consensus   │─→ │ 3. Make SFT           │
│ agent.py             │   │ merge_submissions.py │   │ make_sft.py           │
│ sub_gemini.jsonl     │   │ sub_consensus.jsonl  │   │ sft_data.jsonl        │
│ sub_qwen14b.jsonl    │   │                      │   │                       │
└──────────────────────┘   └──────────────────────┘   └──────────┬───────────┘
                                                                   │
                                                                   ▼
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│ 6. Docker submit     │←─ │ 5. Merge LoRA        │←─ │ 4. Train              │
│ Dockerfile           │   │ (manual sau train)   │   │ train_kaggle.py       │
│ predict.sh           │   │ models/qwen-datamate │   │ + eval_finetune.py    │
│ inference.py         │   │                      │   │ lora_out/final_lora   │
└──────────────────────┘   └──────────────────────┘   └──────────────────────┘
```

## Commands từng bước

### 1. Gen data (ĐANG CHẠY)

```bash
# Local (Gemini)
GEMINI_API_KEY=... DATAMATE_LLM_BACKEND=gemini \
  python3 code/agent.py --split train --data-dir . --save-code --out sub_gemini.jsonl

# Kaggle (Qwen 14B) - đã push v6
```

**Eval baseline** sau khi gen xong:
```bash
python3 code/scorer.py --sub sub_gemini.jsonl --split train
# → overall acc + per-type breakdown
```

### 2. Merge 2 nguồn (consensus voting)

```bash
python3 code/merge_submissions.py \
  --inputs sub_gemini.jsonl sub_qwen14b.jsonl \
  --out sub_consensus.jsonl --min-agree 2
# → giữ câu nào cả 2 model đồng ý (high confidence)
```

### 3. Filter SFT data

```bash
python3 code/make_sft.py \
  --from-submission sub_consensus.jsonl \
  --out sft_data.jsonl \
  --max-chars 14000
# → Length filter + AST dedup + per-type stats
```

### 4. Train trên Kaggle

Upload `sft_data.jsonl` thành dataset Kaggle `datamate-sft`. Chạy notebook:

```python
# Kaggle notebook
!pip install unsloth trl
import os
os.environ["MODEL_NAME"] = "Qwen/Qwen2.5-Coder-7B-Instruct"  # hoặc 14B
os.environ["SFT_DATA_PATH"] = "/kaggle/input/datamate-sft/sft_data.jsonl"
exec(open("/kaggle/input/datamate-code/train_kaggle.py").read())
```

**14B split sessions** (nếu chọn 14B):
```python
# Session 1
os.environ["MODEL_NAME"] = "Qwen/Qwen2.5-Coder-14B-Instruct"
os.environ["LR"] = "1e-4"
os.environ["MAX_STEPS"] = "2500"

# Session 2 (resume)
os.environ["RESUME_CKPT"] = "/kaggle/input/datamate-ckpt-v1/checkpoint-2500"
os.environ["MAX_STEPS"] = "4500"
```

### 5. Eval fine-tuned model

```bash
python3 code/eval_finetune.py \
  --base-model Qwen/Qwen2.5-Coder-7B-Instruct \
  --lora /kaggle/working/lora_out/final_lora \
  --data-dir . \
  --n 200 --seed 42
# → per-type pass@1 breakdown, so với baseline
```

### 6. Merge LoRA → merged model → Docker

```python
# Kaggle (merge step)
from unsloth import FastLanguageModel
model.save_pretrained_merged("qwen-datamate", tokenizer, save_method="merged_16bit")
# Download qwen-datamate/ → đặt vào models/qwen-datamate/
```

```bash
# Local
docker build -t datamate:v1 .

# Smoke test
docker run --gpus all --rm \
  -v $(pwd)/public_test:/data:ro \
  -v $(pwd)/result:/result \
  datamate:v1
```

## Techniques đã áp dụng

| # | Technique | File áp dụng | Impact |
|---|-----------|--------------|--------|
| 1 | Majority voting across k samples | `merge_submissions.py` | +5-8% pass@1 |
| 2 | Type-aware answer matching | `scorer.py` (đã có) | +15-20% filter yield |
| 5 | Retry-on-exception feedback | `agent.py` (đã có, `max_retries=2`) | +3-5% EX |
| 6 | Sequence packing SFT | `train_kaggle.py` `packing=True` | +30-40% throughput |
| 7 | LoRA rank 32, all linears | `train_kaggle.py` | +1-2% pass@1 |
| 8 | Cosine LR + 3% warmup | `train_kaggle.py` | +0.5-1% pass@1 |
| 9 | Early stop on val loss | `train_kaggle.py` `load_best_model_at_end` | tránh overfit |
| 10 | Length filtering > truncation | `make_sft.py` `--max-chars` | tránh hallucination |
| 11 | AST-normalized dedup | `make_sft.py` | +1-3% generalization |
| 12 | Per-type accuracy breakdown | `scorer.py`, `make_sft.py`, `eval_finetune.py` | reveal weak types |

## Chưa áp dụng (nice-to-have)

- #3 Schema serialization as DDL + 3 sample rows (loader đã có 1 sample, có thể tăng)
- #4 Skeleton-based few-shot (phức tạp, cần retriever)
- #13 Abstention threshold calibration (cần logprobs)
- #14 Multi-sheet Excel pre-flatten (loader đã có `__all` version)
- #15 Rulebook compression via retrieval (BM25/MiniLM)

## Files mới/upgraded

| File | Status | Mô tả |
|------|--------|-------|
| `code/scorer.py` | 🔼 Upgraded | +per-type breakdown |
| `code/make_sft.py` | 🔼 Upgraded | +length filter +AST dedup +per-type stats |
| `code/train_kaggle.py` | 🔼 Rewritten | +val split +packing +cosine LR +best ckpt +ENV config |
| `code/inference.py` | 🆕 NEW | Docker entrypoint, per-question logs |
| `code/eval_finetune.py` | 🆕 NEW | Load LoRA, test N câu, per-type report |
| `code/merge_submissions.py` | 🆕 NEW | Consensus voting across submissions |
| `Dockerfile` | 🔼 Updated | Python 3.11, env vars đầy đủ |
| `predict.sh` | 🔼 Updated | Gọi inference.py (không phải agent.py) |
| `requirements.txt` | 🔼 Updated | +peft |
