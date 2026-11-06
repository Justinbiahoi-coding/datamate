# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DataMate** (ZAC 2026 — Zalo AI Challenge 2026) is a Vietnamese natural-language-to-answer challenge over structured tabular data.

**Core task**: Given a business's data files (CSV/Excel/SQLite) + a Vietnamese question + an `as_of_date`, output a correct answer — or decline if the data cannot support the question.

**Example**:
```json
// Input (questions.jsonl line)
{"id": "q_06de33fa21cc", "business_id": "biz_118", "question": "sp bán dc nhiều nhất tuần rồi là gì", "as_of_date": "2026-03-04"}

// Output (submission.jsonl line)
{"id": "q_06de33fa21cc", "type": "string", "answer": "Xi măng Hà Tiên PCB40 bao 50kg"}
```

## Directory Structure

```
datamate/
├── train/
│   ├── data/<biz_id>/          # 30 businesses, each: *.csv|*.xlsx|*.sqlite + README.md
│   ├── questions.jsonl         # 3000 questions (100 input fields each)
│   ├── answers.jsonl           # gold answers (train only); "answer": null = unanswerable
│   ├── rulebook.md             # business rules — MUST read per split (not share across splits)
│   └── calendar.csv            # solar-lunar calendar (for Tết, lunar date expressions)
├── public_test/
│   ├── data/<dev_id>/          # 14 businesses (dev_001..dev_014)
│   ├── questions.jsonl         # 1000 questions
│   ├── rulebook.md             # may differ from train rulebook
│   └── calendar.csv
└── infor/                      # challenge documentation (description, rules, evaluation)
```

## Data Details

### Questions & Answers

Each `questions.jsonl` line:
- `id`: question ID
- `business_id`: which business's data to query
- `question`: Vietnamese natural-language query (informal, typos common)
- `as_of_date`: defines "today" for all relative time expressions ("tháng này", "tuần rồi", etc.)

Each `answers.jsonl` line (train only):
- `id`, `type`, `answer`: matches submission format
- `alias`: alternative accepted spellings for string answers
- `answer: null` → unanswerable

### Answer Types Distribution (train)
| Type | Count | Notes |
|------|-------|-------|
| number | 1884 | 62.8% — most common, include VND amounts |
| percent | 578 | 19.3% — floating point, 2 decimal places |
| list | 193 | 6.4% — ordered list of values |
| date | 145 | 4.8% — specific date answers |
| string | 88 | 2.9% — product names, text answers |
| unanswerable | 70 | 2.3% — data doesn't support the question |
| boolean | 23 | 0.8% — true/false |
| table | 19 | 0.6% — multi-column result |

### Business Data Files
Each business has 1+ data files in multiple possible formats:
- **CSV**: simple flat files (`ban_hang.csv`, `nhap_hang.csv`, etc.)
- **Excel (.xlsx)**: often multi-sheet (one sheet per month), exported from POS software
- **SQLite (.sqlite)**: relational database with multiple tables

Each business also has a `README.md` describing columns, unit conversions, and quirks. Quality varies — some are detailed, some are minimal.

### Business Types Covered
Grocery stores, coffee/bubble-tea shops, restaurants, pharmacies, building-material stores, motorbike repair shops, mother-and-baby stores, and others. Private test may include unseen business types.

## Key Rules (rulebook.md)

The `rulebook.md` is **split-specific** — always read the rulebook of the split being processed, not a cached copy.

Critical default interpretations:
- **Revenue**: sum of line amounts after line discounts; excludes order-level vouchers, VAT, delivery fees; excludes cancelled and returned orders (even partial returns = exclude entire order)
- **"Bán chạy" (best-selling)**: by quantity (converted to base unit), NOT by revenue
- **"Tháng này"**: from day 1 to end of `as_of_date` (not full month)
- **"Tuần trước/tuần rồi"**: full Monday–Sunday of the previous week
- **"Tết năm Y"**: 23rd day of 12th lunar month (year Y-1) to 10th day of 1st lunar month (year Y) — requires `calendar.csv`
- **Debt (công nợ)**: COD orders and e-commerce orders excluded; returns still counted if debt remains
- **Cost (giá vốn)**: weighted average by lot at time of sale; NOT FIFO, NOT last purchase price
- **Gross profit**: use `cost_price` column on each sale line, do NOT recalculate from purchase records

When question phrasing conflicts with the rulebook, follow the question.

## Submission Format

```json
{"id": "q_01240", "type": "table", "answer": [["col1", "col2"], ["val1", "val2"]], "reason": "optional"}
```

- `reason`: optional field, helps with evaluation disputes
- Missing IDs → scored as `abstain`
- `unanswerable` when data cannot support the question
- `abstain` when agent chooses not to answer

**Validate submission**: `python -m zaic_tools --validate submission.jsonl` *(if tool available)*

## Competition Rules

### Key Technical Constraints
1. **Model size**: total parameters across ALL models ≤ **15B** (MoE counts all params, not just active)
2. **Fully offline**: no API calls, no downloads during inference; Docker runs with network disabled
3. **No hard-coding**: cannot use question IDs or business IDs to key answers
4. **Code execution**: agent may generate and execute Python code inside the container (expected but not required)
5. **Data directory**: mounted read-only at `/data`; write temp files elsewhere

### Compute Reference
- **Hardware**: 2× NVIDIA RTX 5090 (32GB VRAM each = 64GB total), 512GB RAM
- **Time limit**: 6 hours wall-clock for entire private test set (including model loading)
- **CUDA**: 12.8 required for Blackwell GPUs (RTX 5090)

### Reproducibility Requirement
- Uploaded PA vs. re-run PA must satisfy: `|PA(uploaded) − PA(re-run)| ≤ 0.03`
- Write per-question logs to `/result/logs/` (at minimum: question ID, final answer, elapsed time)

### Schedule
- **Round 1 (Public test)**: up to 5 submissions/day on leaderboard
- **Solution deadline**: November 16, 2026 23:59 (GMT+7) — submit Docker image
- **Round 2 (Private test)**: November 20–23, 2026 — run frozen solution, upload results
- **Final ranking**: organizers' re-run of Docker on private test

## Docker Submission

The Docker image must include:
- Source code (training + inference)
- Model weights
- `predict.sh`: reads `/data`, writes `/result/submission.jsonl`
- `README.md` describing the solution
- Per-question logs at `/result/logs/`

```bash
# predict.sh entrypoint pattern
#!/bin/bash
python infer.py \
  --data /data \
  --split public_test \  # or private_test
  --out /result/submission.jsonl \
  --logs /result/logs/
```

## Development Workflow

### Scoring locally
```bash
python score.py --split train --sub submission.jsonl
# Or self-check with gold answers:
python score.py --split train --self-check
```

### Key agent pipeline pattern
```python
import json
from pathlib import Path

def infer(question_item, split_root):
    biz_id = question_item["business_id"]
    question = question_item["question"]
    as_of_date = question_item["as_of_date"]
    
    biz_dir = split_root / "data" / biz_id
    rulebook = (split_root / "rulebook.md").read_text()
    calendar = split_root / "calendar.csv"
    
    # 1. Load business README for schema context
    readme = (biz_dir / "README.md").read_text()
    
    # 2. Load data files (CSV/Excel/SQLite)
    # 3. Apply rulebook + as_of_date to scope the query
    # 4. Generate code or SQL → execute → extract answer
    # 5. Format answer with correct type
    
    return {"id": question_item["id"], "type": ..., "answer": ...}
```

### Testing individual questions
```python
# Quick test on a specific business
python agent.py \
  --split train \
  --biz biz_118 \
  --question "sp bán nhiều nhất tuần rồi là gì" \
  --as-of 2026-03-04
```

## Common Pitfalls

### Data Issues
- **Multi-sheet Excel**: each sheet = one month; must iterate all sheets or the right one
- **Column names vary per business**: always read README.md before accessing files
- **Unit conversions**: products sold in cartons/packs but counted in base units (e.g., 1 thùng = 24 lon)
- **Encoding**: files use UTF-8 or UTF-8 BOM; use `encoding='utf-8-sig'` for safety
- **Dates in Vietnamese**: "1 thg 6 2025" format in some CSVs

### Business Logic Issues
- **"Tháng này" ≠ full month**: only up to and including `as_of_date`
- **Same-period comparison**: "so với tháng trước" uses same number of days, not calendar month
- **Returned orders**: even partial return = exclude the ENTIRE order from revenue
- **COD orders**: NOT debt — excluded from accounts receivable
- **"Bán chạy"**: quantity in base units, NOT revenue, NOT number of order lines
- **Lunar calendar**: always use `calendar.csv` for Tết-related calculations

### Scoring Issues
- **number/percent**: must match within tolerance (usually ±1 for rounding)
- **string/list**: fuzzy matching with alias list; normalize whitespace and accents
- **unanswerable**: only when data truly cannot support the question (not just hard to compute)
- **abstain**: lower penalty than wrong answer — use when uncertain

---

**Version**: ZAC 2026 DataMate | **Train**: 3000 questions / 30 businesses | **Public test**: 1000 questions / 14 businesses
