# DataMate — ZAC 2026

Hệ thống trả lời câu hỏi tiếng Việt trên dữ liệu bảng (CSV/Excel/SQLite) doanh nghiệp.

**Deadline**: 16/11/2026 | **Hardware**: 2× RTX 5090 (64GB VRAM) | **Model limit**: ≤15B params

---

## Pipeline tổng quan

```
[Train data 3000 câu]
        │
        ▼
  1. agent.py (Gemini)       ← chạy inference, sinh submission.jsonl
        │
        ▼
  2. scorer.py               ← đánh điểm local (+1/-1/0)
        │
        ▼
  3. make_sft.py             ← lọc câu đúng → tạo SFT dataset
        │
        ▼
  4. Fine-tune Qwen3-14B     ← LoRA trên 2×RTX 5090 (offline)
        │
        ▼
  5. Docker image            ← đóng gói model + code, nộp
        │
        ▼
  6. Public test submit      ← leaderboard, tối đa 5 lần/ngày
```

---

## Cài đặt

```bash
pip install pandas openpyxl xlrd google-generativeai tqdm
```

## Chạy inference (bước 1)

```bash
# Test nhanh 10 câu train
DATAMATE_LLM_BACKEND=gemini \
GEMINI_MODEL=gemini-3.8-flash \
GEMINI_API_KEY=<your_key> \
  python code/agent.py --split train --limit 10 --out submission.jsonl

# Chạy toàn bộ 3000 câu
DATAMATE_LLM_BACKEND=gemini \
GEMINI_MODEL=gemini-3.8-flash \
GEMINI_API_KEY=<your_key> \
  python code/agent.py --split train --out submission.jsonl
```

## Chấm điểm local (bước 2)

```bash
python code/scorer.py --split train --sub submission.jsonl -v
# Output: Correct / Wrong / Abstain + chi tiết câu sai
```

## Tạo SFT data (bước 3)

```bash
python code/make_sft.py \
  --sub submission.jsonl \
  --split train \
  --out sft_data.jsonl
# Lọc các câu agent trả lời đúng → format cho SFT
```

## Fine-tune (bước 4)

```bash
# Chạy trên Kaggle (2×T4) hoặc local 2×RTX5090
python code/train_kaggle.py \
  --data sft_data.jsonl \
  --model Qwen/Qwen3-14B \
  --out ./checkpoints
```

---

## Cấu trúc thư mục

```
datamate/
├── code/
│   ├── agent.py        ← inference chính (LLM + code exec)
│   ├── loader.py       ← đọc CSV/Excel/SQLite
│   ├── scorer.py       ← chấm điểm local
│   ├── make_sft.py     ← tạo SFT dataset
│   └── train_kaggle.py ← fine-tune script
├── train/
│   ├── data/<biz_id>/  ← 30 doanh nghiệp, mỗi doanh nghiệp có file + README.md
│   ├── questions.jsonl ← 3000 câu hỏi
│   ├── answers.jsonl   ← đáp án gold (chỉ có ở train)
│   ├── rulebook.md     ← luật nghiệp vụ (QUAN TRỌNG)
│   └── calendar.csv    ← lịch âm dương (tính Tết, ngày âm)
├── public_test/        ← 1000 câu, 14 doanh nghiệp (không có answers.jsonl)
├── infor/              ← tài liệu cuộc thi
└── submission.jsonl    ← output cuối cùng để nộp
```

---

## Các file quan trọng

### `code/agent.py`
- Đọc câu hỏi → gọi LLM → sinh code pandas/SQL → exec → trích RESULT
- System prompt có các quy tắc nghiệp vụ: cancellation_rate, doanh thu, SoQuy format
- Hàm helper quan trọng: `cancellation_rate()`, `get_month_df()`, `find_revenue_col()`

### `code/loader.py`
- Auto-detect header (skiprows) cho từng loại file
- Hỗ trợ multi-sheet Excel (một sheet/tháng)

### `train/rulebook.md`
- **Đọc trước khi làm bất cứ thứ gì**
- Định nghĩa: doanh thu, bán chạy, tháng này, tuần trước, nợ, giá vốn...

---

## Quy tắc nghiệp vụ quan trọng (tóm tắt)

| Quy tắc | Giá trị mặc định |
|---------|-----------------|
| Doanh thu | Tổng sau giảm giá dòng; loại đơn hủy + hoàn trả |
| Bán chạy | Theo số lượng (quy đổi đơn vị cơ bản), KHÔNG theo doanh thu |
| "Tháng này" | Từ ngày 1 đến as_of_date (không phải cả tháng) |
| "Tuần trước" | Thứ 2 – CN của tuần trước |
| Tỉ lệ hủy | `cancelled_unique / (total - returned)` × 100, KHÔNG dùng len(df) |
| SoQuy | "90.000đ" = 90,000 (dấu chấm = phân cách nghìn) |

---

## Scoring

- **+1** câu đúng
- **-1** câu sai  
- **0** abstain (không trả lời)

Tolerance: number ±1, percent ±0.01

---

## Phân công 4 người

### Người 1 — Agent & Accuracy
**Mục tiêu**: chạy inference toàn bộ 3000 câu train, tối đa hóa accuracy

Làm ngay:
```bash
# Kill process cũ nếu còn
kill <PID>

# Chạy 5 batch song song (mỗi batch 600 câu)
DATAMATE_LLM_BACKEND=gemini GEMINI_MODEL=gemini-3.8-flash GEMINI_API_KEY=<key> \
  python3 code/agent.py --split train --offset 0    --limit 600 --out sub_0.jsonl > log_0.log 2>&1 &

DATAMATE_LLM_BACKEND=gemini GEMINI_MODEL=gemini-3.8-flash GEMINI_API_KEY=<key> \
  python3 code/agent.py --split train --offset 600  --limit 600 --out sub_1.jsonl > log_1.log 2>&1 &

DATAMATE_LLM_BACKEND=gemini GEMINI_MODEL=gemini-3.8-flash GEMINI_API_KEY=<key> \
  python3 code/agent.py --split train --offset 1200 --limit 600 --out sub_2.jsonl > log_2.log 2>&1 &

DATAMATE_LLM_BACKEND=gemini GEMINI_MODEL=gemini-3.8-flash GEMINI_API_KEY=<key> \
  python3 code/agent.py --split train --offset 1800 --limit 600 --out sub_3.jsonl > log_3.log 2>&1 &

DATAMATE_LLM_BACKEND=gemini GEMINI_MODEL=gemini-3.8-flash GEMINI_API_KEY=<key> \
  python3 code/agent.py --split train --offset 2400 --limit 600 --out sub_4.jsonl > log_4.log 2>&1 &

# Merge khi xong
cat sub_0.jsonl sub_1.jsonl sub_2.jsonl sub_3.jsonl sub_4.jsonl > submission_full.jsonl
python3 code/scorer.py --split train --sub submission_full.jsonl -v
```

Output cần có: `submission_full.jsonl` (3000 dòng)

---

### Người 2 — SFT Data Pipeline
**Mục tiêu**: kiểm tra `make_sft.py` hoạt động đúng, tạo SFT dataset sạch

Làm ngay (không cần chờ 3000 câu):
```bash
git clone https://github.com/Justinbiahoi-coding/datamate
cd datamate

# Test với submission nhỏ trước (cần có train/data/ và train/answers.jsonl)
python3 code/make_sft.py --sub submission.jsonl --split train --out sft_test.jsonl

# Xem output
cat sft_test.jsonl | python3 -c "import sys,json; [print(json.dumps(json.loads(l), ensure_ascii=False, indent=2)) for l in sys.stdin]" | head -60
```

Khi Người 1 xong:
```bash
python3 code/make_sft.py --sub submission_full.jsonl --split train --out sft_data.jsonl
wc -l sft_data.jsonl  # nên có ~1500-2000 dòng
```

Output cần có: `sft_data.jsonl`

---

### Người 3 — Fine-tune
**Mục tiêu**: fine-tune Qwen3-8B trên Kaggle, export weights

Làm ngay (không cần chờ SFT data):
1. Mở [kaggle.com/code](https://kaggle.com/code) → New Notebook → GPU T4 ×2
2. Upload `code/train_kaggle.py`
3. Test script chạy được với fake data:
```python
# Test 10 steps để confirm setup
!python train_kaggle.py --model Qwen/Qwen3-8B --data fake --steps 10
```
4. Confirm VRAM < 32GB (2×T4 = 32GB tổng)

Khi có `sft_data.jsonl` từ Người 2:
```bash
python3 code/train_kaggle.py \
  --model Qwen/Qwen3-8B \
  --data sft_data.jsonl \
  --out ./checkpoints
```

Output cần có: checkpoint weights (`.safetensors`)

---

### Người 4 — Docker & Submit
**Mục tiêu**: Docker image chạy được, submit lên leaderboard

Làm ngay (không cần chờ ai):
```bash
git clone https://github.com/Justinbiahoi-coding/datamate
cd datamate
```

Tạo 2 file sau:

**`predict.sh`**:
```bash
#!/bin/bash
set -e
python3 /app/code/agent.py \
  --split ${SPLIT:-public_test} \
  --data-dir /data \
  --out /result/submission.jsonl
```

**`Dockerfile`**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY code/ /app/code/
COPY predict.sh /app/
RUN pip install --no-cache-dir pandas openpyxl xlrd tqdm transformers torch
RUN chmod +x /app/predict.sh
ENTRYPOINT ["/app/predict.sh"]
```

Test build:
```bash
docker build -t datamate .
docker run --rm -v $(pwd)/public_test:/data -v $(pwd)/result:/result datamate
```

Khi có model weights từ Người 3: copy vào image, test lại.

Output cần có: `Dockerfile` + `predict.sh` commit lên repo

---

## Model recommendation

Dựa trên research: **Qwen3-14B** là lựa chọn tốt nhất cho task này:
- Code gen Python/pandas tốt
- Tiếng Việt khá (tốt hơn Llama-3)  
- 14B params đúng giới hạn 15B
- Hỗ trợ LoRA/QLoRA tốt

Chi tiết: `reports/Chọn LLM cho DataMate ZAC 2026.md`
