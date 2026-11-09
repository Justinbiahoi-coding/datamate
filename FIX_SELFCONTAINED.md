# FIX — làm cho 601 đáp án "tự chứa" (self-contained)

Đọc `HANDOFF.md` trước để nắm bối cảnh. File này chỉ nói về một việc: sửa các lời giải đang phụ thuộc file ngoài. **Không chạy Việc B/C trong HANDOFF khi chưa làm xong file này.**

## 1. Vấn đề (đã kiểm chứng bằng cách chạy)

Quét toàn bộ 3.000 dòng của bản gộp `/tmp/merged_3000.jsonl` bằng đúng bộ lọc của `code/verify_selfcontained.py`, có **601 dòng** vi phạm (không phải 570): **600 dòng thuộc 750 câu retry9** và **1 dòng cũ** (`q_c972201b657c`). 600 dòng retry9 chia làm hai kiểu:
- **569 câu** dùng module phụ trong `/tmp/s9_*` (như mô tả dưới đây);
- **31 câu** (batch `retry9_024`) không dùng `/tmp` nhưng vẫn nạp dữ liệu bằng đường dẫn tuyệt đối `/Users/.../train/data/...` qua `sys.path.insert` + `from loader import load_business`. Vì vậy chúng không nằm trong `audit_dependent.json` (danh sách này chỉ lọc `/tmp`) nhưng vẫn hỏng khi đổi máy/chạy Docker.

569 lời giải đầu tiên (`sub_haiku/retry9_*.jsonl`, từ `retry9_006` trở đi) KHÔNG tự chạy được:
- Code bắt đầu bằng `sys.path.insert(0, '/tmp/s9_0xx')` rồi `import h` / `import h112 as H` / `from h129 import ...`. Module phụ (`h.py`, `h112.py` ... `h130.py`) nằm trong `/tmp/s9_0xx/`. Xoá `/tmp` hoặc khởi động lại máy là hỏng cả 569 câu.
- Các module phụ **tự nạp lại dữ liệu từ ổ đĩa** bằng `load_business(ROOT/'train'/'data'/BIZ)` với đường dẫn tuyệt đối `/Users/buivanthien/Learn/zalo chelen/datamate`. Khi chạy thật trong Docker, dữ liệu nằm ở thư mục khác, nên kể cả có gộp file phụ vào code thì lệnh nạp này vẫn hỏng.
- Nếu để nguyên, bộ train sẽ dạy model viết `import h` gọi hàm không tồn tại. Model sẽ cho kết quả lỗi 100% ở các câu kiểu này.

Phạm vi đầy đủ: **601 id** = 569 id ở `audit_dependent.json` khoá `dependent` + 31 id batch `retry9_024` chỉ lệch đường dẫn `/Users` + 1 id cũ `q_c972201b657c`. `audit_dependent.json` nay có thêm các khoá `absolute_only` (31 id), `old_tmp_only` (1 id) và `all_external` (601 id) để tra cứu. Phân bố: 19 business (`biz_105`, `biz_109`–`118`, `biz_121`, `biz_123`–`biz_127`, `biz_129`, `biz_130`).

**Đính chính (2026-11-09):** khoá `currently_broken` (52 id) **không phải lỗi thật**. Các câu này chỉ lỗi khi nhiều file cùng tên `h.py` ở các thư mục `/tmp/s9_*` khác nhau bị nạp trong cùng một tiến trình (`module 'h' has no attribute 't111'/'t110'/'t109'`). Chạy lại từng câu trong tiến trình sạch, hoặc xoá `sys.modules['h']` giữa các câu, thì **cả 52 câu đều chạy đúng**. Các hàm `t109/t110/t111` vẫn còn trong `/tmp/s9_007/h.py`; không cần khôi phục từ `gen*.py`. Đã kiểm chứng 3 mẫu `q_0194d8d10f17`, `q_ee7479a659e6`, `q_1ba969686341` trong tiến trình mới.

Ngoài 569 câu retry9 phụ thuộc `/tmp`, còn 31 câu retry9 chỉ dùng đường dẫn `/Users` (xử lý ở mục G) và 1 câu cũ `q_c972201b657c` trỏ vào `/private/tmp/claude-501/...` (không nằm trong `dependent`). Câu cũ này chỉ thừa dòng `sys.path.insert` (không thực sự import gì từ đó) nên đã bỏ dòng đó và lưu bản sửa ở `sub_selfcontained/other_fix.jsonl`; `verify_selfcontained.py` báo 1/1 ok.

Các module phụ hiện còn trong `/tmp`: `s9_006/h.py`, `s9_007/h.py` (nhiều hàm theo biz, ví dụ `t109/t110/t111`), `s9_009/h112.py`, `s9_010/h113.py`, `s9_011/h114.py`, `s9_012/h115.py` + `h116.py`, `s9_015/h117.py`, `s9_017/h118.py`, `s9_018/h121.py`, `s9_020/h123.py`, `s9_022/h124.py`, `s9_025/h126.py` + `h127.py`, `s9_027/h129.py`, `s9_029/h130.py`. Các script `gen*.py` trong các thư mục này là nơi sinh ra các lời giải. **Sao lưu toàn bộ `/tmp/s9_*` ra `backup_s9/` trong thư mục dự án ngay trước khi làm gì khác** (`cp -r /tmp/s9_* backup_s9/`).

## 2. Yêu cầu với code sau khi sửa
Mỗi lời giải phải tự chạy một mình bên trong `exec_code` (xem `code/agent.py`, hàm `exec_code`):
1. Chỉ `import` thư viện chuẩn, `pandas`, `numpy` (và `re`, `unicodedata`, `math`, `datetime`). **Cấm:** `sys.path`, `load_business`, `from loader`, mọi `import h*`, `open(`, đường dẫn tuyệt đối (`/tmp`, `/Users/...`), đường dẫn `train/data`.
2. **Lấy dữ liệu từ sandbox, không nạp lại từ đĩa.** `exec_code` đã đưa dữ liệu vào code qua hai cách: (a) mỗi khoá cấp cao của dữ liệu là một biến có sẵn (ví dụ `DuLieuBanHang`, `DanhSachHoaDonChiTiet`), và (b) biến `data` là dict chứa đúng các khoá đó. Trong module phụ, thay `load_business(...)` / `biz()` bằng biến `data`. Ví dụ `b = biz()` thành `b = data`. Giữ nguyên phần xử lý phía sau (`D = b['DuLieuBanHang']`, ...).
3. Không sửa trực tiếp DataFrame gốc trong sandbox; dùng `.copy()` (module phụ đã làm vậy ở hầu hết chỗ, giữ nguyên).
4. Giữ phép gán `RESULT = ...` và kết quả **phải trùng với kết quả đã lưu** (`answer` trong dòng gốc). Việc gộp file phụ vào code là biến đổi cơ học, nên kết quả không được thay đổi. Nếu kết quả đổi, đó là lỗi của bước biến đổi, không phải lý do để chỉnh logic cho khớp gold.
5. **Kích thước:** càng gọn càng tốt — mục tiêu lý tưởng dưới ~3.500 ký tự, thực tế chấp nhận tới ~7.500 ký tự (kết quả đợt này: trung vị 4.471, p90 6.406, dài nhất 7.246). Giới hạn cứng là `make_sft.py --max-chars 19000` tính cả prompt (~10k ký tự). Vì vậy **chỉ giữ các hàm thật sự được dùng** (cắt bỏ hàm thừa, xem bước 3.D). Nếu một câu vẫn quá dài, rút gọn bằng cách viết lại phần xử lý cho gọn rồi kiểm tra lại kết quả.
6. Không gọi LLM/API ngoài. Không đọc, in hay dùng giá trị gold. Dùng `answer` đã lưu làm "đáp án chuẩn của phép biến đổi"; chỉ dùng gold qua công cụ `verify_selfcontained.py`.

## 3. Cách làm (làm theo thứ tự)
**A. Chuẩn bị**
```
mkdir -p backup_s9 sub_selfcontained
cp -r /tmp/s9_* backup_s9/
cp -r sub_haiku sub_haiku.bak_before_fix
```
Lấy dòng gốc của từng id trong `dependent` từ `sub_haiku/retry9_*.jsonl` (mỗi id có thể xuất hiện hơn một lần; lấy dòng cuối).

**B. Xác định module phụ của từng câu.** Dùng regex trên `_code` để lấy:
- thư mục từ `sys.path.insert(0, '/tmp/s9_0xx')`;
- tên module từ `import h`, `import h112 as H`, `from h129 import a, b`, `import h, pandas as pd`;
- tên bí danh (`H`, `h`) để biết cách gọi (`H.qty(...)`, `h.tables()`).
Đọc mã nguồn module phụ tại `/tmp/s9_0xx/<module>.py`.

**C. Tạo phiên bản "tự chứa" của module phụ (một lần cho mỗi module, dùng lại cho nhiều câu):**
- Bỏ docstring đầu file và **mọi `Expr` cấp cao** (kể cả `sys.path.insert(...)`), `ROOT = ...`, `from pathlib import Path`, `from loader import load_business`.
- Sửa hàm nạp dữ liệu: trong `biz()` (hoặc tên tương đương) trả về `data` thay vì gọi `load_business`.
- Thay mọi lời gọi `load_business(<đường dẫn>)` (kể cả `load_business(ROOT/'train'/'data'/BIZ)` và `table()` của h118) bằng biến `data`.
- Với `s9_007/h.py`: thay toàn bộ thân `biz(biz_id)` bằng `return data`; thay `t109()` (đang `importlib` đọc `/tmp/s9_006/h.py`) bằng phần `tables()` của biz_109 trong `s9_006/h.py`.
- Nếu module dùng biến toàn cục cache kiểu `_b = None`, có thể giữ nguyên: mỗi lần chạy `exec_code` là một namespace mới. Nếu bỏ cache thì phải bỏ cả `global _b` và mọi chỗ gán/đọc `_b`.

**D. Cắt tỉa hàm thừa (tree-shake) bằng `ast`.** Với mỗi câu:
1. Phân tích code giải (phần sau các dòng import module phụ) và tìm mọi tên được dùng: `h.xxx`, `H.xxx`, hoặc tên nhập trực tiếp bằng `from h129 import a, b`. **Loại `ROOT` và `load_business` khỏi seed** (chúng chỉ là đường dẫn nạp dữ liệu, sẽ được thay bằng `data`).
2. Với module đã sửa ở bước C, tính tập hàm/biến toàn cục cần thiết: bắt đầu từ các tên ở bước 1, thêm mọi hàm/hằng cấp cao mà chúng gọi (đệ quy). Chỉ đưa vào code các `import` an toàn (`re`, `unicodedata`, `pandas`, `numpy`, `math`, `datetime`, `decimal`) và định nghĩa cấp cao thuộc tập đó, theo đúng thứ tự gốc.
3. **Không đưa `ROOT = ...` vào**, kể cả khi nó bị seed do `H.ROOT`. Bỏ mọi `Expr` cấp cao (docstring, `sys.path.insert`).
4. Đổi cách gọi: `H.qty(` và `h.tables(` thành `_h_qty(` và `_h_tables(`. Tốt nhất là prefix **mọi** tên cấp cao của module phụ bằng `_h_` (kể cả `_b`, `norm`) để tránh trùng với biến/hàm của code giải. Khi đổi tên phải đổi cả `Name` ở ngữ cảnh `Store`, `global`, tên `def`, và target của phép gán — không chỉ `Load`.
5. Ghép: `import ...` (pandas/numpy/re/unicodedata) + phần module đã cắt tỉa + phần code giải (đã bỏ các dòng `sys.path.insert`, `import h*`; thay `load_business(...)`/`_lb(...)` bằng `data`).

Khung gợi ý (chỉ là phác thảo, cần chạy thử và sửa):
```python
import ast, re
def top_defs(src):                      # {tên: đoạn mã} cho import, def, gán cấp cao
    tree = ast.parse(src); lines = src.splitlines(); out = {}
    for n in tree.body:
        seg = "\n".join(lines[n.lineno-1:n.end_lineno])
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)): out[n.name] = ("def", seg, n)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name): out[t.id] = ("var", seg, n)
        elif isinstance(n, (ast.Import, ast.ImportFrom)): out[f"__imp{n.lineno}"] = ("imp", seg, n)
    return out
def names_used(node):                   # mọi tên (Name/Attribute gốc) xuất hiện trong node
    return {x.id for x in ast.walk(node) if isinstance(x, ast.Name)}
def reachable(defs, seeds):
    need, stack = set(), list(seeds)
    while stack:
        k = stack.pop()
        if k in need or k not in defs: continue
        need.add(k); stack += list(names_used(defs[k][2]))
    return need
```
Với `H.xxx` / `h.xxx`, dùng `ast` để lấy tên thuộc tính `xxx` làm hạt giống (seed).

**E. Kiểm tra bằng công cụ có sẵn.** Ghi kết quả vào `sub_selfcontained/retry9_fix.jsonl` (cùng định dạng dòng như `sub_haiku`: `id, type, answer, _code, _verdict:"correct", _attempts`), rồi chạy:
```
python3 code/verify_selfcontained.py sub_selfcontained/retry9_fix.jsonl --ids <file json danh sách id> --out sub_selfcontained/verify_report.json
```
Công cụ kiểm tra: (1) tĩnh: không có `sys.path`, `load_business`, đường dẫn tuyệt đối, `open(`, import module phụ; (2) động: chạy với dữ liệu nạp mới cho từng câu, đã chặn các module `h`, `h100..h130`, so khớp với **`answer` đã lưu của chính dòng đó** (đây là phép biến đổi cơ học, phải giữ nguyên kết quả); (3) có `RESULT`. Câu nào không đạt sẽ có lý do trong report. Lặp lại cho đến khi hết lỗi hoặc xác định được câu không sửa nổi.

**Đính chính (2026-11-09):** bản cũ của `verify_selfcontained.py` so khớp cứng với **gold**, nên luôn báo 1 câu sai: `q_2d6cd51e8c40` (code ra 13, gold 12 — câu đúng nhờ dung sai, đã nằm trong `audit_blocklist.json`). Điều này mâu thuẫn với yêu cầu "kết quả phải trùng `answer` đã lưu". Công cụ đã được sửa: mặc định so với `answer` đã lưu; thêm cờ `--check-gold` nếu muốn kiểm tra cứng với gold. Vì vậy tiêu chí `bad 0` áp dụng cho chế độ mặc định; chế độ `--check-gold` sẽ còn đúng 1 câu đã biết.

**F. 52 câu `currently_broken`.** Không cần xử lý riêng: đây là lỗi nạp nhầm module `h` như đã đính chính ở mục 1. Chỉ cần áp dụng quy trình self-contained như 569 câu còn lại (đặc biệt `t109` trong `/tmp/s9_007/h.py` còn `importlib` đọc `/tmp/s9_006/h.py` — phải thay bằng phần `tables()` của biz_109). Nếu sau khi sửa vẫn có câu không chạy, ghi id vào `sub_selfcontained/unfixed.json`, không bịa kết quả.

**G. 31 câu còn lại (chỉ có `/Users`, không có `/tmp`).** Đây là các câu batch `retry9_024` dùng trực tiếp `load_business(Path('/Users/.../train/data/biz_X'))`. Chuyển đổi cơ học bằng `python3 sub_selfcontained/fix_base_absolute.py`: bỏ `sys.path.insert`, `from pathlib import Path`, `from loader import load_business`; thay `b = load_business(...)` bằng `b = data`; chạy lại và so với `answer` đã lưu. Kết quả ghi ở `sub_selfcontained/base_fix.jsonl`. Script chọn đúng các dòng có `/Users` mà không nằm trong `audit_dependent.json`, nên không đụng tới 569 câu đã sửa.

## 4. Tiêu chí hoàn thành
- `verify_selfcontained.py` (chế độ mặc định, so với `answer` đã lưu) báo `bad 0` cho toàn bộ file `sub_selfcontained/all_fix.jsonl` (601 dòng).
- Số câu sửa được: kỳ vọng 601/601. Báo cáo số cụ thể, số câu còn lỗi, và kích thước code trung bình/lớn nhất.
- Mọi câu đã sửa vẫn cho **đúng kết quả đã lưu** (so với `answer` trong dòng gốc).
- Không ghi đè `sub_haiku/` (đã có bản sao `sub_haiku.bak_before_fix`). Bản sửa nằm riêng ở `sub_selfcontained/`.

**Kết quả thực hiện 2026-11-09:** 601/601 câu sửa được, không còn câu lỗi. `sub_selfcontained/all_fix.jsonl` = 569 dòng `retry9_fix.jsonl` + 31 dòng `base_fix.jsonl` + 1 dòng `other_fix.jsonl`; `verify_selfcontained.py` mặc định báo **checked 601 | ok 601 | bad 0**. `unfixed.json` và `base_unfixed.json` đều rỗng. Riêng 569 câu retry9: **checked 569 | ok 569 | bad 0**; chế độ `--check-gold` còn đúng 1 câu `q_2d6cd51e8c40` (đã nằm trong `audit_blocklist.json`). Code dài trung vị 4.471 ký tự, p90 6.406, dài nhất 7.246 — vẫn dưới ngưỡng `make_sft.py --max-chars 19000` khi cộng prompt.

## 5. Sau khi sửa xong (người khác làm, không làm trong phiên này)
Bản sửa đã sẵn sàng ở `sub_selfcontained/all_fix.jsonl` (601 dòng, gồm 569 `retry9_fix` + 31 `base_fix` + 1 `other_fix`; không còn câu lỗi). Ở Việc B của `HANDOFF.md`, khi gộp `sub_sonnet_all.jsonl`, **phải ghi đè dòng của đúng 601 id bằng dòng trong `sub_selfcontained/all_fix.jsonl`**:
```python
import json, os
fix = {json.loads(l)['id']: json.loads(l) for l in open('sub_selfcontained/all_fix.jsonl')}
rows = {json.loads(l)['id']: json.loads(l) for l in open('sub_sonnet_all.jsonl')}
rows.update(fix)    # bản tự chứa thay cho bản phụ thuộc file ngoài
# loại các câu không sửa được, nếu có (file là list các object {"id", "error"})
for name in ('unfixed.json', 'base_unfixed.json'):
    p = f'sub_selfcontained/{name}'
    if os.path.exists(p):
        for item in json.load(open(p)):
            rows.pop(item['id'], None)
open('sub_sonnet_all.jsonl','w').write(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows.values()))
```
Kiểm tra lại ngay sau khi ghi đè:
```
python3 code/verify_selfcontained.py sub_selfcontained/all_fix.jsonl --ids sub_selfcontained/all_ids.json --out sub_selfcontained/all_verify.json
```

Sau đó chạy tiếp `merge_final.py`, bước 2b (loại `audit_blocklist.json`), `make_sft.py`. **Trước khi tạo bộ train, chạy `verify_selfcontained.py` trên toàn bộ file đáp án cuối** để chắc chắn không còn câu nào phụ thuộc file ngoài.

## 6. Lưu ý và cạm bẫy
- Đừng dọn `/tmp/s9_*` cho đến khi bước E báo `bad 0` hoặc đã có bản sao ở `backup_s9/`.
- 569 câu đầu có cùng một kiểu lỗi, nên sửa theo từng module (khoảng 17 module), không sửa tay từng câu; 31 câu còn lại chỉ lệch đường dẫn `/Users` nên sửa bằng script `fix_base_absolute.py`.
- Nếu hàm nạp dữ liệu trong module phụ khác hẳn mẫu `biz()` ở trên (ví dụ `h.py` ở `s9_007` có nhiều business, dùng `_biz[biz_id] = load_business(...)`), đọc kỹ và đổi sao cho mỗi câu chỉ dùng đúng dữ liệu của business hiện tại trong `data`.
- Các lỗi sửa chưa đủ gồm cả những lỗi đã biết ở `HANDOFF.md` (mục "Bài học"). Đừng gỡ cảnh báo đó.
- `audit_blocklist.json` (26 id) là một danh sách khác (code hỏng/lệch gold); đừng nhầm với `audit_dependent.json`.
