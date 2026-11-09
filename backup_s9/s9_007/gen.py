"""Generate solution files for batch retry9_007."""
from pathlib import Path

OUT = Path('/tmp/s9_007')
OUT.mkdir(exist_ok=True)

PRE_A = '''import sys
sys.path.insert(0, '/tmp/s9_007')
import h, pandas as pd

t = h.t109()
hd, ct, sp = t['hd'], t['ct'], t['sp']
ok = hd['st_norm'] == 'ok'


def month_mask(y, m):
    s = pd.Timestamp(year=y, month=m, day=1)
    e = s + pd.offsets.MonthBegin(1)
    return ok & (hd['dt'] >= s) & (hd['dt'] < e)


def lines_in(mask):
    return ct[ct['Mã hóa đơn'].isin(set(hd.loc[mask, 'Mã hóa đơn']))]
'''

PRE_B = '''import sys
sys.path.insert(0, '/tmp/s9_007')
import h, pandas as pd

t = h.t110()
hd = t['hd']
ok = hd['st_norm'] == 'ok'


def day_mask(day):
    d = pd.Timestamp(day)
    return (hd['dt'] >= d) & (hd['dt'] < d + pd.Timedelta(days=1))


def month_mask(y, m):
    s = pd.Timestamp(year=y, month=m, day=1)
    e = s + pd.offsets.MonthBegin(1)
    return ok & (hd['dt'] >= s) & (hd['dt'] < e)
'''

PRE_C = '''import sys
sys.path.insert(0, '/tmp/s9_007')
import h, pandas as pd

u = h.t111()
don, ct, sp, kh, tt = u['don'], u['ct'], u['sp'], u['kh'], u['tt']
ok = don['st_norm'] == 'ok'


def month_mask(dt, y, m):
    return h.month_mask(dt, y, m)


def order_ids(mask):
    return set(don.loc[mask, 'Mã chứng từ'])


def lines_in(mask):
    return ct[ct['Ma don'].isin(order_ids(mask))]


def revenue(mask):
    return float(lines_in(mask)['ttien'].sum())


def qty_of_size(y, m, size):
    sub = lines_in(ok & month_mask(don['dt'], y, m)).merge(sp[['SKU', 'size']], left_on='ID SP', right_on='SKU')
    sub = sub[(sub['size'] == size) & (sub['Đơn vị (tính)'] == 'ly')]
    return int(round(float(sub['slqd'].sum())))


def qty_of_product(y, m, name):
    sku = sp.loc[sp['name_n'] == h.norm(name), 'SKU'].iloc[0]
    sub = lines_in(ok & month_mask(don['dt'], y, m))
    return int(round(float(sub.loc[sub['ID SP'] == sku, 'slqd'].sum())))
'''

S = {}

# ── biz_109 ────────────────────────────────────────────────────────────────
S['q_ee7479a659e6'] = ('A', '''
sub = lines_in(month_mask(2026, 2)).merge(sp[['Mã hàng', 'Nhóm hàng(3 Cấp)']], on='Mã hàng')
sub = sub[sub['Nhóm hàng(3 Cấp)'].astype(str).str.strip().str.lower() == 'thuốc lá']
RESULT = int(round(float(sub['Thành tiền_n'].sum())))
''')

S['q_f5c395d7ac02'] = ('A', '''
sub = lines_in(month_mask(2025, 8))
RESULT = int(round(float(sub['Thành tiền_n'].sum())))
''')

# ── biz_110 ────────────────────────────────────────────────────────────────
S['q_1ba969686341'] = ('B', '''
RESULT = int(round(float(hd.loc[month_mask(2026, 4), 'rev'].sum())))
''')
S['q_2673cb45d798'] = ('B', '''
RESULT = int(ok.sum() and (ok & day_mask('2026-05-03')).sum())
''')
S['q_6fe9f968ba88'] = ('B', '''
RESULT = int(round(float(hd.loc[month_mask(2026, 6), 'rev'].sum())))
''')

for qid, day in [('q_72c84fa63b2a', '2025-06-13'), ('q_9187bd6c41c9', '2025-12-16'),
                 ('q_f50a0876a46e', '2025-12-11'), ('q_f6b49fedf388', '2025-08-15')]:
    S[qid] = ('B', f'''
RESULT = int(round(float(hd.loc[ok & day_mask('{day}'), 'rev'].sum())))
''')

for qid, day in [('q_9cd8322bf3b4', '2026-05-18'), ('q_a2632be14081', '2025-07-06'),
                 ('q_a8efcf429886', '2026-01-22'), ('q_b3a4f8dd6cb4', '2025-11-19'),
                 ('q_d96f45ce61be', '2026-03-02'), ('q_fe444980c217', '2026-05-27')]:
    S[qid] = ('B', f'''
RESULT = int(round(float(hd.loc[ok & day_mask('{day}'), 'rev'].sum())))
''')

S['q_dc2e6bc8362b'] = ('B', '''
RESULT = int((ok & day_mask('2026-05-27')).sum())
''')

# ── biz_111 ────────────────────────────────────────────────────────────────
S['q_0194d8d10f17'] = ('C', '''
d = don[(don['Số KH'].notna()) & (don['Số KH'].astype(str).str.strip() != '')]
d = d[(d['st_norm'] != 'cancel') & (d['conlai'] > 0)]
d = d[d['Phương thức TT'].astype(str).str.strip().str.lower() != 'cod']
RESULT = int(d['Số KH'].nunique())
''')

S['q_0e81c97f3e09'] = ('C', '''
RESULT = qty_of_size(2025, 11, 'M')
''')
S['q_133c0dd807b7'] = ('C', '''
m = ok & month_mask(don['dt'], 2026, 1)
n = int(m.sum())
RESULT = int(round(revenue(m) / n)) if n else 0
''')
S['q_1a79715010d5'] = ('C', '''
start = pd.Timestamp('2026-08-01')
end = pd.Timestamp('2026-08-19') + pd.Timedelta(days=1)
m = ok & (don['dt'] >= start) & (don['dt'] < end)
sub = lines_in(m).merge(sp[['SKU', 'size']], left_on='ID SP', right_on='SKU')
sub = sub[(sub['size'] == 'M') & (sub['Đơn vị (tính)'] == 'ly')]
RESULT = int(round(float(sub['slqd'].sum())))
''')
S['q_1dcd312143bb'] = ('C', '''
m = (don['st_norm'] == 'cancel') & month_mask(don['dt'], 2025, 7)
RESULT = int(m.sum())
''')
S['q_2915e15dff0b'] = ('C', '''
RESULT = qty_of_size(2025, 2, 'L')
''')
S['q_2c97f6f308e9'] = ('C', '''
m = ok & (don['dt'] >= pd.Timestamp('2025-07-01')) & (don['dt'] < pd.Timestamp('2025-10-01'))
RESULT = int(m.sum())
''')
S['q_34f94cccddb7'] = ('C', '''
RESULT = qty_of_product(2025, 2, 'Cà phê sữa (L)')
''')
S['q_4a3cf2a9214e'] = ('C', '''
RESULT = qty_of_product(2025, 7, 'Nước ép dưa hấu (L)')
''')

PRE = {'A': PRE_A, 'B': PRE_B, 'C': PRE_C}

for qid, (variant, body) in S.items():
    (OUT / f'{qid}.py').write_text(PRE[variant] + body)
print('wrote', len(S), 'solutions')
