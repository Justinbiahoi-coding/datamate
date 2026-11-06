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

## Phân công công việc gợi ý

| Task | Mô tả | Priority |
|------|-------|----------|
| Tăng accuracy Gemini | Debug các câu sai trong train, tune system prompt | 🔴 Cao |
| Tạo SFT data | Chạy full 3000 câu, chạy make_sft.py | 🔴 Cao |
| Fine-tune Qwen3-14B | LoRA training trên dữ liệu SFT | 🔴 Cao |
| Docker packaging | Đóng gói model + predict.sh | 🟡 Trung |
| Public test submit | Test trên leaderboard | 🟡 Trung |

---

## Model recommendation

Dựa trên research: **Qwen3-14B** là lựa chọn tốt nhất cho task này:
- Code gen Python/pandas tốt
- Tiếng Việt khá (tốt hơn Llama-3)  
- 14B params đúng giới hạn 15B
- Hỗ trợ LoRA/QLoRA tốt

Chi tiết: `reports/Chọn LLM cho DataMate ZAC 2026.md`
