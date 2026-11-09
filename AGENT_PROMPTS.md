# Prompt mẫu để giao việc cho sub agent (Sonnet)

Luôn tạo agent bằng `model: "sonnet"`. Tạo từng agent một, khoảng 10 agent mỗi đợt. Sau mỗi đợt agent, chạy `code/apply_overlay.py` để kiểm tra độc lập và gộp (agent tự báo "đúng" chưa đủ tin). Mỗi batch ghi kết quả đúng vào `sub_haiku/<prefix>_NNN.jsonl` thông qua `code/haiku_check.py`.

Thay `NNN` bằng số batch (ví dụ `000`) trong cả đường dẫn batch, thư mục `/tmp/sXX_NNN/` và tên file kết quả.

## 1. Viết gọn code dài  (batches: `batches_compact/compact_NNN.jsonl`, prefix `compact`)
```
You are an expert Python/pandas data analyst. The file /Users/buivanthien/Learn/zalo chelen/datamate/batches_compact/compact_NNN.jsonl has 20 Vietnamese business questions. Work in that folder (cd "/Users/buivanthien/Learn/zalo chelen/datamate"). Do NOT call any external LLM/API; YOU write the code.

Each line has: id, business_id, question, as_of_date (treat as "today"), `_old_code` = an existing WORKING solution that is far too long, and gold fields (_gold_type, _gold_answer, _gold_alias) that you must NOT open, print or use.

TASK: rewrite each `_old_code` into a COMPACT, readable, self-contained pandas solution that produces the SAME RESULT. It will be a training example for a small model, so it must be short, clear and general (derive everything from the data and as_of_date; never hardcode an answer).

Per question:
1. Read `_old_code` and the question. Understand what rule it implements (tables/columns, excluded statuses, dedup, name normalization, unit conversion, date range, rounding). Keep every rule that matters; drop helper functions and handling this question does not need.
2. To inspect data: sys.path.insert(0,'code'); from loader import load_business; b=load_business(Path('train/data')/BIZ); b is a dict of DataFrames + b['_readme'] (README with column meanings and quirks). The rulebook is train/rulebook.md.
3. Write the new code to /tmp/s13_NNN/<id>.py. It runs via code/agent.py exec_code: every top-level key of the data dict is a variable in scope, plus `data` (dict of the same), helpers to_num(series), parse_date(series), vn_normalize(text), and as_of_date. Assign the answer to RESULT with the same type as the old code (number -> int/float; percent -> string like '2.08%'; date -> 'YYYY-MM-DD'/'YYYY-MM'; list; boolean; string; table dict; or "unanswerable"). Do not print.
4. Requirements: under 1500 characters (hard limit 2500) and at least 40% shorter than the old code. Fully SELF-CONTAINED: only import pandas/numpy/re/unicodedata/math/datetime/decimal. FORBIDDEN: sys.path, load_business, any helper-module import, open(), absolute paths (/tmp, /Users), 'train/data', and the shortcuts cancellation_rate() and find_revenue_col(). Copy DataFrames with .copy() before modifying. Clear variable names; no unreadable one-liner golf.
5. Grade: python3 code/haiku_check.py batches_compact/compact_NNN.jsonl <id> /tmp/s13_NNN/<id>.py . It prints CORRECT/WRONG (gold hidden; STRICT exact match) and saves correct rows to sub_haiku/compact_NNN.jsonl. If WRONG, you dropped a rule that matters: compare with `_old_code`, restore it, retry (up to 4 attempts). If you cannot reach the size target, skip the question (save nothing). Never save a version that is not shorter than the old code.

Reply with ONE line: how many saved / 20, and the ids skipped.
```
Gộp: `python3 code/apply_overlay.py --prefix compact --require-shorter --src sub_final5.jsonl --out sub_final6.jsonl`

## 2. Viết lại câu có ngày tương đối để dùng `as_of_date`  (batches: `batches_dates/dates_NNN.jsonl`, prefix `dates`)
Đây là 228 câu có từ như "hôm nay", "tuần trước", "tháng này", "N ngày gần nhất" mà code đang ghi cứng ngày. Model phải học tính ngày từ `as_of_date` bằng code (pandas), không tự nhẩm lịch.
```
You are an expert Python/pandas data analyst. The file /Users/buivanthien/Learn/zalo chelen/datamate/batches_dates/dates_NNN.jsonl has 20 Vietnamese business questions. Work in that folder (cd "/Users/buivanthien/Learn/zalo chelen/datamate"). Do NOT call any external LLM/API; YOU write the code.

Each line has: id, business_id, question, as_of_date (= "today"), `_old_code` = a WORKING solution that HARDCODES calendar dates (e.g. '2025-08-01'..'2025-08-31') for a relative expression in the question, and gold fields (_gold_type, _gold_answer, _gold_alias) that you must NOT open, print or use.

TASK: rewrite each `_old_code` so every date that follows from a relative expression in the question ("hôm nay", "hôm qua", "tuần này/trước", "tháng này/trước", "N ngày gần nhất", "từ đầu năm", "đến hết hôm nay", "quý này/trước", "cùng kỳ"...) is COMPUTED FROM the variable as_of_date with pandas (pd.Timestamp(as_of_date), pd.Timedelta, pd.offsets, .replace(day=1), .weekday()), never typed as a literal. The result at the given as_of_date must stay EXACTLY the same. Dates the question states explicitly ("tháng 3/2025", "ngày 15/08/2026") may stay literal. Follow the rulebook train/rulebook.md for the meaning of each expression (week starts Monday; 'tháng này' = day 1 to end of today; 'N ngày gần nhất' includes today; 'tháng này so với tháng trước' compares the same number of days; 'tính đến hôm nay' = state at end of today from the start of the data).
Keep everything else; you may also shorten the code (target under 1500 characters).

Per question:
1. Read `_old_code` and the question; decide which dates are relative. To inspect data: sys.path.insert(0,'code'); from loader import load_business; b=load_business(Path('train/data')/BIZ); b is a dict of DataFrames + b['_readme'].
2. Write the new code to /tmp/s14_NNN/<id>.py. It runs via code/agent.py exec_code: every top-level key of the data dict is a variable in scope, plus `data`, helpers to_num(series), parse_date(series), vn_normalize(text), and as_of_date. Assign RESULT with the same type as the old code. Do not print.
3. Requirements: uses as_of_date. Fully SELF-CONTAINED: only import pandas/numpy/re/unicodedata/math/datetime/decimal. FORBIDDEN: sys.path, load_business, helper-module import, open(), absolute paths, 'train/data', cancellation_rate(), find_revenue_col(). Copy DataFrames with .copy() before modifying.
4. Grade: python3 code/haiku_check.py batches_dates/dates_NNN.jsonl <id> /tmp/s14_NNN/<id>.py . CORRECT/WRONG (gold hidden; STRICT exact) and saves correct rows to sub_haiku/dates_NNN.jsonl. If WRONG, you changed the meaning of a date; compare with `_old_code`, fix, retry (up to 4 attempts). If you cannot, skip it (save nothing).
5. Extra sanity (strongly recommended): run your code with another as_of_date (e.g. 10 days later) via exec_code and check the dates it computes are the ones the question means (print them in a scratch run; do not leave prints in the saved code).

Reply with ONE line: how many saved / 20, and the ids skipped.
```
Gộp: `python3 code/apply_overlay.py --prefix dates --require-asof --src sub_final6.jsonl --out sub_final7.jsonl` (hoặc `--src sub_final5.jsonl` nếu bỏ qua việc viết gọn).

## 3. Giải lại một câu từ đầu (khi một câu không đạt kiểm định)
Dùng prompt ở `HANDOFF.md` mục 8 (cấm đọc gold, cấm `cancellation_rate()`/`find_revenue_col()`, bắt buộc code tự chứa, chấm bằng `haiku_check.py`). Tạo batch từ các id không đạt, mỗi dòng gồm `id, business_id, question, as_of_date, _gold_type, _gold_answer, _gold_alias` (xem `code/make_batches_next.py` làm mẫu cách ghi `item()`).

## 4. Sau khi gộp xong
```
python3 code/make_sft.py --from-submission <file mới> --out sft_data_vN.jsonl --max-chars 45000 --no-dedup --prompt-version v2
```
Rồi tách lại tập kiểm tra bằng `holdout_ids.json` (giữ nguyên danh sách id để so sánh các lần train): bộ train = mọi dòng của `sft_data_vN.jsonl` có `id` không nằm trong `holdout_ids.json`.
