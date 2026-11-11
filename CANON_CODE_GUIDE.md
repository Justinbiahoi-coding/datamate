# Chuẩn hóa code mẫu — hướng dẫn cho agent (đọc hết file này trước khi làm)

## 0. Prompt để dán cho agent điều phối

```
Làm việc trong thư mục /Users/buivanthien/Learn/zalo chelen/datamate (cd vào đó). Đọc kỹ file CANON_CODE_GUIDE.md và làm đúng theo đó: bạn là agent điều phối cho việc viết lại code mẫu (1.609 câu hỏi chia 81 batch). Bước đầu chạy `python3 code/canon_status.py --next 10` để biết batch nào còn thiếu (đã có sẵn một phần kết quả, đừng làm lại phần đã xong). Nếu bạn tạo được sub-agent thì mỗi batch một sub-agent (tối đa 10 chạy song song) dùng prompt ở mục 5; nếu không thì tự làm lần lượt từng batch theo đúng prompt đó. Trước tiên làm thử một batch rồi kiểm tra tỉ lệ được chấp nhận theo mục 6. Sau mỗi đợt, chạy lệnh gộp ở mục 6. Khi hết lượt hoặc hết batch, dừng và báo cáo theo mục 8. Không sửa các file ở mục 9.
```

## 1. Việc này để làm gì

Chẩn đoán ngày 11/11/2026: model 7B sau 2 phiên train chỉ đúng 2/5 câu đã train và 0/9 câu hold-out. Một nguyên nhân đo được ở dữ liệu train:

- 56% mẫu tự định nghĩa hàm phụ, với **154 tên hàm khác nhau** cho vài khái niệm giống nhau (`money`, `_h_money`, `_h_mnum`, `rev`, `revenue`…), trong đó **115 phiên bản hàm đọc tiền**.
- Độ dài code chênh nhiều (trung vị 600 đến 1.400 ký tự theo nguồn sinh; nhiều mẫu hơn 4.000 ký tự).
- Với khoảng 2.800 mẫu và 1–2 epoch, model nhỏ không học nổi nhiều kiểu viết cho cùng một việc, nên nó chép đoạn hàm phụ của mẫu này sang câu khác và sai.

**Mục tiêu:** viết lại các mẫu về **một kiểu viết duy nhất, ngắn, dùng hàm có sẵn của môi trường chạy**, giữ nguyên đáp án (đúng tuyệt đối).

## 2. Hiện trạng và dữ liệu có sẵn

- Bảng code gốc (3.000 câu, đã kiểm định đúng): `sub_final6.jsonl`. **Không sửa.**
- Batch cần làm: `batches_canon/canon_000.jsonl` … `canon_080.jsonl` (81 batch, 1.609 câu, 20 câu mỗi batch; đã sắp code dài nhất trước; không có câu hold-out).
- Kết quả đã làm: `sub_haiku/canon_NNN.jsonl` (một file mỗi batch). **Đã có kết quả của các batch 000, 001, 003, 004, 007, 009 (106 câu, đã kiểm định độc lập: đều đúng).**
- **Xem còn thiếu gì:** `python3 code/canon_status.py --next 10` in ra 10 batch tiếp theo còn câu chưa làm kèm danh sách id cần làm. Một câu tính là xong khi đã có dòng lưu đạt các quy tắc tĩnh (không `def`, ≤ 1.500 ký tự, ngắn hơn code cũ, còn dùng `as_of_date` nếu code cũ có dùng, không dính mẫu cấm). Chỉ làm các id được liệt kê; **bỏ qua id đã xong**.
- Chấm 1 câu (giấu đáp án, đúng tuyệt đối, ghi kết quả đúng vào `sub_haiku/canon_NNN.jsonl`): `python3 code/haiku_check.py batches_canon/canon_NNN.jsonl <id> <file.py>`.

Mỗi dòng batch có: `id, business_id, question, as_of_date, _old_code` và `_gold_type, _gold_answer, _gold_alias`. **Không ai được mở, in hay dùng các trường `_gold_*`**; chúng chỉ để `haiku_check.py` chấm.

## 3. Hàm có sẵn khi code chạy (`code/agent.py`, hàm `exec_code`)

Mọi bảng dữ liệu của doanh nghiệp là biến có sẵn theo tên file (ví dụ `DanhSachHoaDon`), cùng với:

| Tên | Dùng cho |
|---|---|
| `as_of_date` | chuỗi `YYYY-MM-DD`, là "hôm nay" |
| `pd` | pandas |
| `data` | dict mọi bảng (kể cả sheet con `ten_file__ten_sheet`) |
| **`money(x)`** | đọc tiền kiểu Việt Nam, nhận số lẻ hoặc Series: `1.200.000đ`, `1,200,000`, `25,000.0000`, `129 000`, `41k`, `2tr900`, `16,56tr`, `-45.000đ` → float (NaN nếu không phải số). **Dùng cho mọi cột tiền.** |
| `to_num(s)` | số thuần (`1234`, `1,234`). **Không dùng cho tiền dạng `1.200.000`** (ra NaN). |
| `parse_date(s)` | ngày: ISO, `dd/mm/yyyy`, `1 thg 5 2026`, số serial Excel |
| `vn_normalize(s)` (= `normalize_text`) | bỏ dấu, gộp khoảng trắng, chữ thường; để so khớp tên |
| `join_by_name(left, lcol, right, rcol, vcol)` | nối theo tên đã chuẩn hóa |
| `get_month_df(stem, year, month)` | lấy sheet theo tháng khi file nhiều sheet |
| `get_rx_product_names(drug_df, sp_df)` | tên thuốc kê đơn (nhà thuốc) |

**Cấm dùng:** `cancellation_rate()`, `find_revenue_col()` (cài sẵn nhưng sai ngữ nghĩa ở nhiều trường hợp).

## 4. Kiểu viết chuẩn (bắt buộc)

1. **Không `def`.** Không tự định nghĩa hàm. Được dùng `lambda` ngắn trong `.apply/.map`. Code có `def` sẽ bị từ chối khi gộp.
2. **Dùng hàm có sẵn ở mục 3** thay cho hàm tự viết: tiền → `money(...)`, ngày → `parse_date(...)`, so tên → `vn_normalize(...)`.
3. **Thứ tự cố định:**
   1. lấy bảng, `.copy()`, bỏ trùng nếu cần (`drop_duplicates`);
   2. đổi kiểu: `parse_date`, `money`;
   3. xác định kỳ: ngày tương đối **tính từ `as_of_date`** (`pd.Timestamp(as_of_date)`, `pd.Timedelta`, `pd.offsets`); ngày ghi rõ trong câu hỏi thì được viết thẳng;
   4. lọc theo rulebook (loại đơn hủy, đơn có trả hàng…), khớp trạng thái bằng `str.contains(..., case=False, na=False)` trên các giá trị thật của cột;
   5. tính toán;
   6. gán `RESULT` đúng kiểu (number → int/float; percent → chuỗi `f"{x:.2f}%"`; date → `'YYYY-MM-DD'`; list; bool; string; bảng dạng dict; hoặc `"unanswerable"`).
4. **Tên biến thống nhất** khi có bảng tương ứng: `orders` (đơn/hóa đơn), `lines` (chi tiết đơn), `products`, `customers`, `stock` (tồn kho), `imports` (phiếu nhập), `import_lines` (chi tiết nhập), `period` hoặc `start`/`end` cho kỳ. Bảng khác đặt tên tiếng Anh ngắn, rõ nghĩa.
5. **Ngắn:** mục tiêu dưới 1.000 ký tự, **giới hạn cứng 1.500**, và phải ngắn hơn code cũ.
6. Tối đa 3 dòng chú thích ngắn, chỉ để gọi tên quy tắc rulebook (ví dụ `# rulebook: loại cả đơn có trả hàng`). Không `print`.
7. Tự chứa: chỉ `import` pandas/numpy/re/unicodedata/math/datetime/decimal. **Cấm:** `sys.path`, `load_business`, import module tự viết, `open(`, đường dẫn tuyệt đối, `'train/data'`.
8. Nếu code cũ dùng `as_of_date` thì code mới **phải** dùng `as_of_date` (không được quay lại ngày viết cứng).

Ví dụ đạt chuẩn (câu `q_406dd570776d`, đã chạy ra đúng đáp án):

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

## 5. Prompt cho từng sub-agent (mỗi sub-agent một batch)

Thay `NNN` (ví dụ `005`) ở mọi chỗ. Chạy khoảng 10 sub-agent song song mỗi đợt. Nếu không tạo được sub-agent thì tự làm từng batch với đúng prompt này. Dùng model mạnh nhất bạn có; nếu là model miễn phí, làm thử đúng một batch trước và kiểm tra tỉ lệ ở mục 6.

```
You are an expert Python/pandas data analyst. Work in /Users/buivanthien/Learn/zalo chelen/datamate (cd there). The file batches_canon/canon_NNN.jsonl has up to 20 Vietnamese business questions. Do NOT call any external LLM/API; YOU write the code. Only do these ids (the others are already done): <PASTE THE IDS FROM canon_status.py>.

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

Reply with ONE line: how many saved, and the ids skipped.
```

## 6. Kiểm định độc lập và gộp (chạy sau mỗi đợt)

Agent tự báo "đúng" là chưa đủ tin. Lệnh dưới đọc **toàn bộ** `sub_haiku/canon_*.jsonl`, chạy lại từng code trên dữ liệu sạch và so đúng tuyệt đối:

```
cd "/Users/buivanthien/Learn/zalo chelen/datamate"
python3 code/apply_overlay.py --prefix canon --src sub_final6.jsonl --out sub_final7.jsonl \
  --require-shorter --forbid-def --max-chars 1500 --keep-asof
python3 code/canon_status.py --next 10
```

- In ra `candidates N | applied A | rejected R`; lý do từ chối ở `sub_final7.jsonl.rejected.json`.
- Luôn dùng `--src sub_final6.jsonl` (bảng gốc), để chạy lại nhiều lần không bị cộng dồn sai. Câu bị từ chối giữ nguyên code cũ, không mất gì.
- **Thử một batch với model mới:** sau batch thử, chạy lệnh trên rồi xem `applied/candidates`. Mốc tham chiếu từ model đã làm trước đó: 106 trên 120 câu thử (khoảng 88%). Từ khoảng 75% trở lên thì cho chạy tiếp; thấp hơn nhiều thì báo lại để đổi model.
- Có thể chạy lệnh gộp bất cứ lúc nào, kể cả khi mới xong một phần.

## 7. Hết lượt giữa chừng

Mỗi câu được ghi ngay khi chấm đúng, nên dừng bất cứ lúc nào cũng không mất gì và không bị trùng (`apply_overlay.py` lấy dòng cuối cho mỗi id). Muốn tiếp tục: chạy `python3 code/canon_status.py --next 10` rồi làm tiếp các id còn thiếu. **Làm theo thứ tự batch tăng dần** (code dài nhất ở các batch đầu, ảnh hưởng lớn nhất). Nếu hết thời gian, cắt ở khoảng 40–50 batch đầu là chấp nhận được.

## 8. Báo cáo khi dừng

Chạy lệnh ở mục 6 rồi báo lại cho người dùng:
1. `applied/rejected` và các lý do từ chối chính;
2. `python3 code/canon_status.py` (số câu xong, số câu còn lại);
3. thống kê trên `sub_final7.jsonl`: số câu còn `def` và độ dài trung vị so với `sub_final6.jsonl`;
4. 3 cặp code cũ/mới đọc ngẫu nhiên: code mới có đúng kiểu ở mục 4 và không bỏ quy tắc nào không.

Tiêu chí chấp nhận khi xong toàn bộ: `applied` ≥ khoảng 70% của 1.609.

## 9. Không được sửa

`code/agent.py`, `code/haiku_check.py`, `code/apply_overlay.py`, `code/canon_status.py`, `sub_final6.jsonl`, `batches_canon/*`, `train/*`. Chỉ ghi vào `sub_haiku/canon_*.jsonl` (qua `haiku_check.py`), `/tmp/s15_*`, và `sub_final7.jsonl`.

## 10. Việc sau đó (người dùng và Claude làm, không phải agent này)

Dựng lại dữ liệu train từ `sub_final7.jsonl` bằng `code/make_sft.py` với prompt v3 rồi train lại:

```
python3 code/make_sft.py --from-submission sub_final7.jsonl --out sft_data_v7.jsonl --max-chars 45000 --no-dedup --prompt-version v3
```
