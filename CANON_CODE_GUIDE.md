# Chuẩn hóa code mẫu (bước 2) — hướng dẫn cho agent điều phối

## 1. Vì sao làm việc này

Chẩn đoán ngày 11/11/2026 (model 7B sau 2 phiên train: đúng 2/5 câu đã train, 0/9 câu hold-out):

- 56% mẫu train tự định nghĩa hàm phụ, có **154 tên hàm khác nhau** cho vài khái niệm giống nhau (`money`, `_h_money`, `_h_mnum`, `rev`, `revenue`…), trong đó **115 phiên bản hàm đọc tiền**.
- Độ dài code chênh nhiều theo nguồn sinh (median 600 đến 1.400 ký tự).
- Với ~2.800 mẫu và 1–2 epoch, model nhỏ không học nổi nhiều kiểu viết cho cùng một việc. Nó chép đoạn hàm phụ của mẫu này sang câu khác và sai.

Mục tiêu: viết lại các mẫu về **một kiểu viết duy nhất, ngắn, dùng hàm có sẵn của môi trường chạy**, giữ nguyên đáp án (đúng tuyệt đối, như kiểm định cũ).

## 2. Đầu vào đã chuẩn bị sẵn

| Thứ | Ở đâu |
|---|---|
| Bảng code hiện tại (3.000 câu, đã kiểm định đúng) | `sub_final6.jsonl` |
| Batch cần làm: **81 batch, 1.609 câu** (code có `def` hoặc dài hơn 1.200 ký tự; không gồm câu hold-out) | `batches_canon/canon_000.jsonl` … `canon_080.jsonl` (sắp theo code dài nhất trước) |
| Tạo lại batch nếu cần | `python3 code/make_batches_canon.py --src sub_final6.jsonl` |
| Chấm 1 câu (giấu đáp án, đúng tuyệt đối, lưu nếu đúng) | `python3 code/haiku_check.py <batch> <id> <file.py>` → ghi vào `sub_haiku/canon_NNN.jsonl` |
| Kiểm định độc lập và gộp | `code/apply_overlay.py` (mục 6) |

Mỗi dòng batch có: `id, business_id, question, as_of_date, _old_code` và `_gold_type, _gold_answer, _gold_alias`. **Agent không được mở, in hay dùng các trường `_gold_*`**; chúng chỉ để `haiku_check.py` chấm.

## 3. Hàm có sẵn khi code chạy (`code/agent.py`, hàm `exec_code`)

Mọi bảng dữ liệu của doanh nghiệp là biến có sẵn theo tên file (ví dụ `DanhSachHoaDon`), cùng với:

| Tên | Dùng cho |
|---|---|
| `as_of_date` | chuỗi `YYYY-MM-DD`, là "hôm nay" |
| `pd` | pandas |
| `data` | dict mọi bảng (kể cả sheet con `ten_file__ten_sheet`) |
| **`money(x)`** (mới) | đọc tiền kiểu Việt Nam, nhận số lẻ hoặc Series: `1.200.000đ`, `1,200,000`, `25,000.0000`, `129 000`, `41k`, `2tr900`, `16,56tr`, `-45.000đ` → float (NaN nếu không phải số). **Dùng cho mọi cột tiền.** |
| `to_num(s)` | số thuần (`1234`, `1,234`). **Không dùng cho tiền dạng `1.200.000`** (ra NaN). |
| `parse_date(s)` | ngày: ISO, `dd/mm/yyyy`, `1 thg 5 2026`, số serial Excel |
| `vn_normalize(s)` (= `normalize_text`) | bỏ dấu, gộp khoảng trắng, chữ thường; để so khớp tên |
| `join_by_name(left, lcol, right, rcol, vcol)` | nối theo tên đã chuẩn hóa |
| `get_month_df(stem, year, month)` | lấy sheet theo tháng khi file nhiều sheet |
| `get_rx_product_names(drug_df, sp_df)` | tên thuốc kê đơn (nhà thuốc) |

**Cấm dùng:** `cancellation_rate()`, `find_revenue_col()` (cài sẵn nhưng sai ngữ nghĩa ở nhiều trường hợp).

## 4. Kiểu viết chuẩn (bắt buộc)

1. **Không `def`.** Không tự định nghĩa hàm. Được dùng `lambda` ngắn trong `.apply/.map`. Code kiểm định sẽ bị từ chối nếu có `def`.
2. **Dùng hàm có sẵn ở mục 3** thay cho hàm tự viết: tiền → `money(...)`, ngày → `parse_date(...)`, so tên → `vn_normalize(...)`.
3. **Thứ tự cố định:**
   1. lấy bảng, `.copy()`, bỏ trùng nếu cần (`drop_duplicates`);
   2. đổi kiểu: `parse_date`, `money`;
   3. xác định kỳ: ngày tương đối **tính từ `as_of_date`** (`pd.Timestamp(as_of_date)`, `pd.Timedelta`, `pd.offsets`), ngày ghi rõ trong câu hỏi thì được viết thẳng;
   4. lọc theo rulebook (loại đơn hủy, đơn có trả hàng…), khớp trạng thái bằng `str.contains(..., case=False, na=False)` trên các giá trị thật của cột;
   5. tính toán;
   6. gán `RESULT` đúng kiểu (number → int/float; percent → chuỗi `f"{x:.2f}%"`; date → `'YYYY-MM-DD'`; list; bool; string; bảng dạng dict; hoặc `"unanswerable"`).
4. **Tên biến thống nhất** khi có bảng tương ứng: `orders` (đơn/hóa đơn), `lines` (chi tiết đơn), `products`, `customers`, `stock` (tồn kho), `imports` (phiếu nhập), `import_lines` (chi tiết nhập), `period` hoặc `start`/`end` cho kỳ. Bảng khác đặt tên tiếng Anh ngắn, rõ nghĩa.
5. **Ngắn:** mục tiêu dưới 1.000 ký tự, **giới hạn cứng 1.500**, và phải ngắn hơn code cũ.
6. Tối đa 3 dòng chú thích ngắn, chỉ để gọi tên quy tắc rulebook (ví dụ `# rulebook: loại cả đơn có trả hàng`). Không `print`.
7. Tự chứa: chỉ `import` pandas/numpy/re/unicodedata/math/datetime/decimal. **Cấm:** `sys.path`, `load_business`, import module tự viết, `open(`, đường dẫn tuyệt đối, `'train/data'`.
8. Nếu code cũ dùng `as_of_date` thì code mới **phải** dùng `as_of_date` (không được quay lại ngày viết cứng).

Ví dụ đạt chuẩn (câu `q_406dd570776d`, đã có trong dữ liệu):

```python
orders = DanhSachHoaDon.drop_duplicates('Mã hóa đơn').copy()
orders['dt'] = parse_date(orders['Thời gian']).dt.normalize()
orders = orders[~orders['Trạng thái'].str.contains('hủy|huỷ|trả', case=False, na=False)]
customers = DanhSachKhachHang
loyal = set(customers[customers['Nhóm khách hàng'] == 'thân thiết']['Mã khách hàng'])
orders = orders[orders['Mã KH'].isin(loyal) & (orders['dt'] >= '2026-03-01') & (orders['dt'] <= '2026-03-31')]
lines = DanhSachHoaDonChiTiet.drop_duplicates()
lines = lines[lines['Mã hóa đơn'].isin(orders['Mã hóa đơn'])]
RESULT = int(round(money(lines['Thành tiền']).sum()))
```

## 5. Prompt giao cho từng agent

Dùng model `sonnet`. Mỗi agent làm **một** batch. Chạy khoảng 10 agent mỗi đợt. Thay `NNN` (ví dụ `000`) ở mọi chỗ.

```
You are an expert Python/pandas data analyst. Work in /Users/buivanthien/Learn/zalo chelen/datamate (cd there). The file batches_canon/canon_NNN.jsonl has 20 Vietnamese business questions. Do NOT call any external LLM/API; YOU write the code.

Each line has: id, business_id, question, as_of_date (= "today"), `_old_code` = a WORKING, verified solution, and gold fields (_gold_type, _gold_answer, _gold_alias) that you must NOT open, print or use.

TASK: rewrite each `_old_code` into the CANONICAL STYLE below. The result at the given as_of_date must stay EXACTLY the same. Read CANON_CODE_GUIDE.md sections 3 and 4 first; they are the rules.

Canonical style (summary — the guide is authoritative):
- NO `def`. Short lambdas inside .apply/.map are fine.
- Use the runtime helpers instead of hand-written ones: money(x) for EVERY money column (handles 1.200.000đ, 1,200,000, 25,000.0000, 41k, 2tr900, 16,56tr), parse_date(s) for dates, vn_normalize(s) for name matching. to_num only for plain numbers. Never use cancellation_rate() or find_revenue_col().
- Fixed order: tables (.copy(), drop_duplicates) -> types (parse_date, money) -> period (relative dates computed from as_of_date; dates stated in the question may be literal) -> rulebook filters (status matching with str.contains(..., case=False, na=False)) -> compute -> RESULT with the same type as the old code.
- Variable names: orders, lines, products, customers, stock, imports, import_lines, start/end; other tables: short clear English names.
- Under 1000 chars ideally, HARD LIMIT 1500, and shorter than `_old_code`. At most 3 short comments naming a rulebook rule. No print.
- If `_old_code` uses as_of_date, your code MUST use as_of_date.
- Self-contained: only import pandas/numpy/re/unicodedata/math/datetime/decimal. FORBIDDEN: sys.path, load_business, helper-module imports, open(, absolute paths, 'train/data'.

Per question:
1. Read `_old_code` and the question; identify every rule it implements (tables, dedup, excluded statuses, unit conversion, period, rounding). Keep every rule that changes the result; drop only helper machinery.
2. To inspect data: import sys; sys.path.insert(0,'code'); from loader import load_business; from pathlib import Path; b=load_business(Path('train/data')/BIZ). b is a dict of DataFrames + b['_readme']. Rulebook: train/rulebook.md. Check that money() parses the money columns you use (no unexpected NaN).
3. Write the new code to /tmp/s15_NNN/<id>.py.
4. Grade: python3 code/haiku_check.py batches_canon/canon_NNN.jsonl <id> /tmp/s15_NNN/<id>.py . It prints CORRECT/WRONG (gold hidden; STRICT exact match) and saves correct rows to sub_haiku/canon_NNN.jsonl. If WRONG, you dropped or changed a rule: compare with `_old_code`, fix, retry (up to 4 attempts). If you cannot make it both correct and canonical, skip it (save nothing). Never save code that still has `def` or exceeds 1500 chars.

Reply with ONE line: how many saved / 20, and the ids skipped.
```

## 6. Sau mỗi đợt: kiểm định độc lập và gộp

Agent tự báo "đúng" là chưa đủ tin. Sau mỗi đợt, gộp **tất cả** các batch `canon_*` đã có (lệnh đọc toàn bộ `sub_haiku/canon_*.jsonl`, chạy lại từng code trên dữ liệu sạch và so đúng tuyệt đối):

```
cd "/Users/buivanthien/Learn/zalo chelen/datamate"
python3 code/apply_overlay.py --prefix canon --src sub_final6.jsonl --out sub_final7.jsonl \
  --require-shorter --forbid-def --max-chars 1500 --keep-asof
```

- In ra `candidates N | applied A | rejected R`. Lý do từ chối ở `sub_final7.jsonl.rejected.json`.
- Luôn dùng `--src sub_final6.jsonl` (bảng gốc), để chạy lại nhiều lần không bị cộng dồn sai.
- Câu bị từ chối giữ nguyên code cũ, không mất gì.

Theo dõi tiến độ: batch `NNN` xong khi có file `sub_haiku/canon_NNN.jsonl`.

```
ls sub_haiku/canon_*.jsonl | wc -l          # số batch đã có kết quả
```

## 7. Tiêu chí chấp nhận khi xong

1. `applied` ≥ khoảng 70% của 1.609. Nếu thấp hơn, xem lý do trong `.rejected.json` và chạy lại batch có tỉ lệ thấp.
2. Đọc ngẫu nhiên 10 cặp code cũ/mới: code mới đúng kiểu ở mục 4, không bỏ quy tắc nào.
3. Thống kê trên `sub_final7.jsonl` (chỉ câu train, không tính hold-out): số câu còn `def` và median độ dài phải giảm rõ so với `sub_final6.jsonl`.
4. Báo lại cho mình: `applied/rejected`, các lý do từ chối chính, và 3 thống kê ở trên.

## 8. Việc sau đó (mình làm, không phải agent)

Dựng lại dữ liệu train từ `sub_final7.jsonl` bằng `code/make_sft.py` **sau khi** phần bổ sung prompt (bước 1) xong, vì prompt cũng thay đổi:

```
python3 code/make_sft.py --from-submission sub_final7.jsonl --out sft_data_v7.jsonl --max-chars 45000 --no-dedup --prompt-version v2
```

## 9. Lưu ý

- Ước tính usage: 81 batch × 1 agent. Các đợt trước mỗi agent mất khoảng 2–3 phút cho 20 câu; tổng chi phí phụ thuộc gói của bạn.
- Không sửa `code/agent.py`, `code/haiku_check.py`, `code/apply_overlay.py`, `sub_final6.jsonl`.
- Nếu một batch lỗi giữa chừng, chạy lại agent cho batch đó; `apply_overlay.py` lấy dòng cuối cho mỗi id nên không bị trùng.
