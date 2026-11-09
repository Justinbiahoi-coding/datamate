"""Self-generate verified SFT records for pilot questions (no external LLM).

Each solution is hand-written from the business README/schema, executed on the
real business data, and only kept if the result matches the gold answer.

Usage:
    python code/gen_self_pilot.py
    python code/gen_self_pilot.py --out pilot/sft_self_pilot.jsonl
"""
import json
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "code"))
from loader import load_business, describe_business  # noqa: E402
from scorer import match_answer  # noqa: E402
from agent import exec_code, infer_type, SYSTEM_PROMPT, build_prompt  # noqa: E402


def make_messages(prompt: str, code: str):
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": f"```python\n{code.strip()}\n```"},
    ]


def result_matches_gold(result, gold_type, gold_ans, alias):
    if result is None:
        return gold_ans is None or gold_type == "unanswerable"
    if gold_ans is None:
        return str(result).lower() in ("unanswerable", "none", "null", "")
    pred_type, pred_val = infer_type(result)
    return match_answer(pred_type, pred_val, gold_type, gold_ans, alias)


# (qid, code)
SOLUTIONS = {
    # biz_109, boolean: revenue increasing 4/2026 -> 5/2026 -> 6/2026?
    "q_e210942807ec": r'''
import pandas as pd
asof = pd.to_datetime(as_of_date)
hd = DuLieuBanHang['DanhSachHoaDon'].copy()
hd['_d'] = parse_date(hd['Thời gian'])
bad = hd['Trạng thái'].astype(str).str.contains('hủy|huỷ|hoàn hàng|trả lại|hoàn trả|trả hàng', case=False, na=False)
hd = hd[~bad]
hd['_rev'] = to_num(hd['Tổng tiền hàng'])
def month_rev(y, m):
    msk = (hd['_d'].dt.year == y) & (hd['_d'].dt.month == m) & (hd['_d'] <= asof)
    return hd.loc[msk, '_rev'].sum()
r4, r5, r6 = month_rev(2026, 4), month_rev(2026, 5), month_rev(2026, 6)
RESULT = bool(r4 < r5 < r6)
''',

    # biz_109, date: day with highest revenue in 4/2025
    "q_77de8b009478": r'''
import pandas as pd
hd = DuLieuBanHang['DanhSachHoaDon'].copy()
hd['_d'] = parse_date(hd['Thời gian'])
bad = hd['Trạng thái'].astype(str).str.contains('hủy|huỷ|hoàn hàng|trả lại|hoàn trả|trả hàng', case=False, na=False)
hd = hd[~bad]
hd = hd[(hd['_d'].dt.year == 2025) & (hd['_d'].dt.month == 4)]
hd['_rev'] = to_num(hd['Tổng tiền hàng'])
by_day = hd.groupby(hd['_d'].dt.date)['_rev'].sum()
RESULT = str(by_day.idxmax())
''',

    # biz_111, list: Zalo OA vs store revenue in 2/2026 (detail line revenue)
    "q_6b90b5fe0a20": r'''
import pandas as pd
asof = pd.to_datetime(as_of_date)
dh = don_hang.copy()
dh['_d'] = parse_date(dh['NgayBan'])
dh = dh[~dh['Xử lý'].astype(str).str.contains('cancel|return', case=False, na=False)]
dh = dh[(dh['_d'].dt.year == 2026) & (dh['_d'].dt.month == 2) & (dh['_d'] <= asof)]
valid_ids = set(dh['Mã chứng từ'].astype(str))
ct = chi_tiet_don.copy()
ct['_rev'] = to_num(ct['T.Tiền'])
ct = ct[ct['Ma don'].astype(str).isin(valid_ids)]
rev_by_channel = dh[['Mã chứng từ', 'Bán qua']].drop_duplicates('Mã chứng từ').merge(
    ct.groupby('Ma don')['_rev'].sum().rename('_rev'),
    left_on='Mã chứng từ', right_index=True, how='inner'
).groupby('Bán qua')['_rev'].sum()
def asnum(x):
    x = float(x)
    return int(round(x)) if abs(x - round(x)) < 1e-6 else x
RESULT = [asnum(rev_by_channel.get('zalo_oa', 0)), asnum(rev_by_channel.get('store', 0))]
''',

    # biz_106, number: total size-L cups sold this month
    "q_25e68617a9f7": r'''
import pandas as pd
asof = pd.to_datetime(as_of_date)
hd = DanhSachHoaDon.copy()
hd['_d'] = parse_date(hd['Thời gian'])
bad = hd['Trạng thái'].astype(str).str.contains('hủy|huỷ|hoàn hàng|trả lại|hoàn trả|trả hàng', case=False, na=False)
hd = hd[~bad & (hd['_d'] >= asof.replace(day=1)) & (hd['_d'] <= asof)]
valid_ids = set(hd['Mã hóa đơn'].astype(str))
ct = pd.concat([DanhSachHoaDonChiTiet_1, DanhSachHoaDonChiTiet_2], ignore_index=True).drop_duplicates()
ct = ct[ct['Mã hóa đơn'].astype(str).isin(valid_ids)]
mask = ct['Tên hàng'].astype(str).str.contains(r'\(L\)', case=False, na=False, regex=True) & \
       ct['Đơn vị tính'].astype(str).str.contains('ly', case=False, na=False)
RESULT = int(round(to_num(ct.loc[mask, 'Số lượng quy đổi']).sum()))
''',

    # biz_109, percent: bánh kẹo share of revenue in 2/2026
    "q_fa6d3acdd604": r'''
import pandas as pd
hd = DuLieuBanHang['DanhSachHoaDon'].copy()
hd['_d'] = parse_date(hd['Thời gian'])
bad = hd['Trạng thái'].astype(str).str.contains('hủy|huỷ|hoàn hàng|trả lại|hoàn trả|trả hàng', case=False, na=False)
hd = hd[~bad & (hd['_d'].dt.year == 2026) & (hd['_d'].dt.month == 2)]
valid_ids = set(hd['Mã hóa đơn'].astype(str))
ct = DanhSachHoaDonChiTiet.copy()
ct['_rev'] = to_num(ct['Thành tiền'])
ct = ct[ct['Mã hóa đơn'].astype(str).isin(valid_ids)]
sp = DuLieuBanHang['DanhSachSanPham'][['Mã hàng', 'Nhóm hàng(3 Cấp)']].drop_duplicates('Mã hàng')
ct = ct.merge(sp, on='Mã hàng', how='left')
total = ct['_rev'].sum()
bakery = ct[ct['Nhóm hàng(3 Cấp)'].astype(str).str.contains('bánh kẹo', case=False, na=False)]['_rev'].sum()
RESULT = f"{round(bakery / total * 100, 2):.2f}%" if total else "0.00%"
''',

    # biz_114, string: best-selling product in 6/2025 by base-unit quantity
    "q_00d4d6380d03": r'''
import pandas as pd
df = ban_hang.copy()
df['_d'] = parse_date(df['Ngày'])
df = df[(df['_d'].dt.year == 2025) & (df['_d'].dt.month == 6)]
bad = df['trang_thai'].astype(str).str.contains('hủy|huỷ|hoàn hàng|trả lại|hoàn trả|trả hàng', case=False, na=False)
bad_ids = set(df.loc[bad, 'Mã GD'].astype(str))
df = df[~df['Mã GD'].astype(str).isin(bad_ids)]
df['_q'] = to_num(df['Quy ra ĐV lẻ'])
sales = df.groupby('Sản phẩm')['_q'].sum()
RESULT = sales.idxmax() if len(sales) else "unanswerable"
''',

    # biz_127, table: top-5 customers by remaining debt as of 2026-07-28
    "q_4c974b445a53": r'''
import pandas as pd
asof = pd.to_datetime(as_of_date)
dh = don_hang.copy()
dh['_d'] = parse_date(dh['Ngày'])
dh = dh[dh['_d'] <= asof]
dh = dh[(dh['Tình trạng'].astype(str) != 'cancelled') & (dh['Trả bằng'].astype(str) != 'cod')]
dh['_debt'] = to_num(dh['Còn nợ'])
debt = dh.groupby(dh['Customer ID'].astype(str))['_debt'].sum()
debt = debt[debt > 0].sort_values(ascending=False).head(5)
kh = khach_hang.copy()
name_map = dict(zip(kh['Mã KH'].astype(str), kh['Khách hàng (tên)'].astype(str)))
rows = [[name_map.get(cid, cid), int(round(v))] for cid, v in debt.items()]
RESULT = {"columns": ["khach_hang", "so_tien_no"], "rows": rows}
''',

    # biz_103, unanswerable: stock is not in the data
    "q_73fac0fa2e46": r'''
# biz_103 only has DonHang_ChiTiet + DanhSachQuyDoi; there is no inventory/stock table.
RESULT = "unanswerable"
''',

    # biz_112, boolean: revenue increasing 5/2025 -> 6/2025 -> 7/2025?
    "q_7c42bbc16fde": r'''
import pandas as pd
asof = pd.to_datetime(as_of_date)
def month_rev(y, m):
    df = get_month_df('So_chi_tiet_ban_hang_1', y, m)
    if df is None:
        return None
    df = df.copy().drop_duplicates()
    bad = df['Trạng thái'].astype(str).str.contains('hủy|huỷ|hoàn hàng|trả lại|hoàn trả|trả hàng|cancel', case=False, na=False)
    bad_ids = set(df.loc[bad, 'Mã đơn hàng'].astype(str))
    df = df[~df['Mã đơn hàng'].astype(str).isin(bad_ids)]
    df['_d'] = parse_date(df['Ngày'])
    df = df[df['_d'] <= asof]
    rev_col = find_revenue_col(df)
    return to_num(df[rev_col]).sum()
r5, r6, r7 = month_rev(2025, 5), month_rev(2025, 6), month_rev(2025, 7)
RESULT = bool(r5 < r6 < r7)
''',

    # biz_130, date: month with highest revenue among 2,3,4/2025
    "q_ab5e0a06f4c1": r'''
import pandas as pd
asof = pd.to_datetime(as_of_date)
df = pd.concat([So_chi_tiet_ban_hang_1, So_chi_tiet_ban_hang_2], ignore_index=True).drop_duplicates()
df['_d'] = parse_date(df['Ngày'])
bad = df['Trạng thái'].astype(str).str.contains('hủy|huỷ|hoàn hàng|trả lại|hoàn trả|trả hàng|cancel', case=False, na=False)
bad_ids = set(df.loc[bad, 'Mã đơn hàng'].astype(str))
df = df[~df['Mã đơn hàng'].astype(str).isin(bad_ids)]
df = df[df['_d'] <= asof]
rev_col = find_revenue_col(df)
df['_rev'] = to_num(df[rev_col])
vals = {}
for m in (2, 3, 4):
    msk = (df['_d'].dt.year == 2025) & (df['_d'].dt.month == m)
    vals[m] = df.loc[msk, '_rev'].sum()
best = max(vals, key=vals.get)
RESULT = f"2025-{best:02d}"
''',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "pilot" / "sft_self_pilot.jsonl"))
    args = parser.parse_args()

    split_root = ROOT / "train"
    rulebook = (split_root / "rulebook.md").read_text(encoding="utf-8")
    with open(split_root / "questions.jsonl", encoding="utf-8") as f:
        q_index = {json.loads(l)["id"]: json.loads(l) for l in f if l.strip()}
    with open(split_root / "answers.jsonl", encoding="utf-8") as f:
        gold_index = {json.loads(l)["id"]: json.loads(l) for l in f if l.strip()}

    records = []
    ok = fail = 0
    for qid, code in SOLUTIONS.items():
        item = q_index[qid]
        gold = gold_index[qid]
        biz_dir = split_root / "data" / item["business_id"]
        try:
            biz_data = load_business(biz_dir)
            result = exec_code(code, biz_data, item["as_of_date"])
        except Exception as e:
            print(f"FAIL exec {qid} ({item['business_id']}): {e}", flush=True)
            fail += 1
            continue

        matched = result_matches_gold(
            result, gold["type"], gold["answer"], gold.get("alias", [])
        )
        pred_t, pred_v = infer_type(result)
        print(
            f"{qid} {item['business_id']}: matched={matched} "
            f"pred=({pred_t}, {pred_v!r}) gold=({gold['type']}, {gold['answer']!r})",
            flush=True,
        )
        if not matched:
            fail += 1
            continue

        biz_schema = describe_business(biz_dir)
        prompt = build_prompt(
            item["question"], item["as_of_date"], biz_schema, rulebook[:2000]
        )
        records.append(
            {
                "id": qid,
                "messages": make_messages(prompt, code),
                "gold_type": gold["type"],
                "gold_answer": gold["answer"],
                "biz_id": item["business_id"],
            }
        )
        ok += 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nWrote {ok} records to {out} (fail={fail})", flush=True)


if __name__ == "__main__":
    main()
