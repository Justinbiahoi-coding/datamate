import json, subprocess, os, sys
from pathlib import Path

Path('/tmp/s9_000').mkdir(parents=True, exist_ok=True)

HEADER = '''import unicodedata, re, math
d = pd.concat([SoBanHang_1__all, SoBanHang_2026__all], ignore_index=True)
d = d[d['Mã hóa đơn'].notna()].copy()
d = d.drop_duplicates()
def money(s):
    s = unicodedata.normalize('NFC',str(s)).strip().lower().replace('đ','').replace(' ','')
    if s in ('','nan','none'): return float('nan')
    neg = s.startswith('-'); s = s.lstrip('-')
    if s.endswith('k'): v = float(s[:-1].replace(',','.'))*1000
    else: v = float(s.replace('.','').replace(',',''))
    return -v if neg else v
d['amt'] = d['Trị giá'].map(money)
d['dt'] = parse_date(d['Ngày giao dịch'])
d['nm'] = d['Hàng'].map(lambda s: re.sub(r'\\s+',' ',unicodedata.normalize('NFC',str(s))).strip().casefold())
st = d['Status'].map(lambda s: unicodedata.normalize('NFC',str(s)).lower())
d['bad'] = st.str.contains('hủy|huỷ|trả')|(d['so_luong']<0)
badord = set(d.loc[d['bad'],'Mã hóa đơn'])
ok = d[~d['Mã hóa đơn'].isin(badord)].copy()
def per(df,a,b): return df[(df['dt']>=a)&(df['dt']<=b)]
def rd(x): return int(math.floor(x+0.5))
'''

solutions = {
    'q_2b96cf7eb6b3': HEADER + '''
x = per(ok, '2026-01-01', '2026-01-31')
RESULT = int(x.amt.sum())
''',

    'q_3edc92c7d0cb': HEADER + '''
x = per(ok, '2026-01-01', as_of_date)
RESULT = int(x.amt.sum())
''',

    'q_4239d9d46ec8': HEADER + '''
x = per(ok, '2026-05-01', '2026-05-31')
first_hours = x.groupby('Mã hóa đơn')['Giờ'].first()
first_hours_dt = pd.to_datetime(first_hours)
morning_orders = set(first_hours[first_hours_dt.dt.hour.between(6, 13)].index)
RESULT = int(x[x['Mã hóa đơn'].isin(morning_orders)].amt.sum())
''',

    'q_4cd6d580fd0b': HEADER + '''
x = per(ok, '2025-05-01', '2025-05-31')
g = x.groupby('Mã hóa đơn').amt.sum()
RESULT = int((g >= 55000).sum())
''',

    'q_4d18e8298871': HEADER + '''
x = per(ok, '2025-09-01', '2025-09-30')
RESULT = rd(x.groupby('Mã hóa đơn').amt.sum().mean())
''',

    'q_560be4fe7b19': HEADER + '''
x = per(ok, '2025-12-15', '2025-12-21')
RESULT = int(x.amt.sum())
''',

    'q_576da3a138ac': HEADER + '''
x = per(ok, '2025-10-01', '2025-10-31')
first_hours = x.groupby('Mã hóa đơn')['Giờ'].first()
first_hours_dt = pd.to_datetime(first_hours)
afternoon_orders = set(first_hours[first_hours_dt.dt.hour.between(14, 21)].index)
RESULT = int(x[x['Mã hóa đơn'].isin(afternoon_orders)].amt.sum())
''',

    'q_5b5c9f36b825': HEADER + '''
x = per(ok, '2026-01-01', '2026-03-31')
RESULT = int(x['Mã hóa đơn'].nunique())
''',

    'q_5c87fb634a59': HEADER + '''
x = per(ok, '2026-02-01', '2026-02-28')
g = x.groupby('Mã hóa đơn').amt.sum()
RESULT = int((g >= 56000).sum())
''',

    'q_694138906f3c': HEADER + '''
m3 = per(d, '2026-03-01', '2026-03-31')
m3_st = m3['Status'].map(lambda s: unicodedata.normalize('NFC',str(s)).lower())
canc_orders = set(m3.loc[m3_st.str.contains('hủy|huỷ'), 'Mã hóa đơn'])
RESULT = len(canc_orders)
''',

    'q_6f4071352ef1': HEADER + '''
x = per(ok, '2025-09-01', '2025-09-30')
m = x['nm'].str.contains('nước ép cam') & x['nm'].str.contains(r'\\(m\\)|\\bm\\b')
RESULT = int(x.loc[m, 'so_luong'].sum())
''',

    'q_7095290807ca': HEADER + '''
x = per(ok, '2026-05-01', '2026-05-31')
m = x['nm'].str.contains('trà sữa trân châu') & x['nm'].str.contains(r'\\(l\\)|\\bl\\b')
RESULT = int(x.loc[m, 'so_luong'].sum())
''',

    'q_74716eae9c4f': HEADER + '''
x = per(ok, '2026-03-23', '2026-03-29')
RESULT = rd(x.groupby('Mã hóa đơn').amt.sum().mean())
''',

    'q_7cc0801e4226': HEADER + '''
x = per(ok, '2025-06-01', '2025-06-30')
g = x.groupby('Mã hóa đơn').amt.sum()
RESULT = int((g >= 130000).sum())
''',

    'q_7f1a8dc3f220': HEADER + '''
m9 = per(d, '2025-09-01', '2025-09-30')
m9_st = m9['Status'].map(lambda s: unicodedata.normalize('NFC',str(s)).lower())
canc_orders = set(m9.loc[m9_st.str.contains('hủy|huỷ'), 'Mã hóa đơn'])
RESULT = len(canc_orders)
''',

    'q_80928271d24c': HEADER + '''
x = per(ok, '2026-03-16', '2026-03-22')
RESULT = rd(x.groupby('Mã hóa đơn').amt.sum().mean())
''',

    'q_82bbd5d8b28c': HEADER + '''
bg = BangGia.copy()
bg['dt'] = parse_date(bg['Ngày áp dụng'])
bg['nm'] = bg['ten_hang'].map(lambda s: unicodedata.normalize('NFC',str(s)).strip().casefold())
bg_croissant = bg[bg['nm'].str.contains('croissant') & (bg['dt'] <= '2026-05-21')].sort_values('dt')
RESULT = int(money(bg_croissant.iloc[-1]['Giá mới']))
''',

    'q_835e49f85406': HEADER + '''
tk = TonKho.copy()
tk['nm'] = tk['Hàng hóa'].map(lambda s: unicodedata.normalize('NFC',str(s)).strip().casefold())
RESULT = int(tk.loc[tk['nm'].str.contains('tiramisu'), 'Tồn cuối'].iloc[0])
''',

    'q_83ff27d651b0': HEADER + '''
cro = ok[ok['nm'].str.contains('croissant')].copy()
cro['sl'] = to_num(cro['so_luong'])
before = cro[(cro.dt >= '2025-07-21') & (cro.dt <= '2025-07-27')].sl.sum()
after = cro[(cro.dt >= '2025-07-28') & (cro.dt <= '2025-08-03')].sl.sum()
pct = round((after - before) / before * 100, 2)
RESULT = f"{pct:.2f}%"
''',

    'q_8ee3f3222d9f': HEADER + '''
x = per(ok, '2026-04-06', '2026-04-12')
first_hours = x.groupby('Mã hóa đơn')['Giờ'].first()
first_hours_dt = pd.to_datetime(first_hours)
afternoon_orders = set(first_hours[first_hours_dt.dt.hour.between(14, 21)].index)
RESULT = len(afternoon_orders)
''',

    'q_8f9439750230': HEADER + '''
x = per(ok, '2025-11-01', '2025-11-30')
m = x['nm'].str.contains('trân châu đen')
RESULT = int(x.loc[m, 'amt'].sum())
''',

    'q_921850fde380': HEADER + '''
x = per(ok, '2026-03-01', '2026-03-31')
m = x['nm'].str.contains(r'\\(m\\)|\\bm\\b') & (x['Unit'].str.lower() == 'ly')
RESULT = int(x.loc[m, 'so_luong'].sum())
''',

    'q_967a2d6503b4': HEADER + '''
x = per(ok, '2026-02-16', '2026-02-22')
RESULT = int(x['Mã hóa đơn'].nunique())
''',

    'q_982f5bc2303c': HEADER + '''
x = per(ok, '2025-05-01', '2025-05-31')
RESULT = rd(x.groupby('Mã hóa đơn').amt.sum().mean())
''',

    'q_9f94997e453d': HEADER + '''
x = per(ok, '2025-08-01', '2025-08-31')
m = x['nm'].str.contains('sinh tố bơ') & x['nm'].str.contains(r'\\(m\\)|\\bm\\b')
RESULT = int(x.loc[m, 'so_luong'].sum())
'''
}

correct_count = 0
for qid, code_str in solutions.items():
    code_path = f"/tmp/s9_000/{qid}.py"
    Path(code_path).write_text(code_str)
    cmd = [".venv/bin/python", "code/haiku_check.py", "batches_retry9/retry9_000.jsonl", qid, code_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    out = res.stdout.strip()
    status = "CORRECT" if "CORRECT" in out else "WRONG"
    if status == "CORRECT":
        correct_count += 1
    print(f"[{qid}] {status}: {out}")

print(f"\nBATCH 000 FINISHED: {correct_count}/25 correct!")
