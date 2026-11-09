"""Generate solution files for batch retry9_008 (biz_111)."""
from pathlib import Path

OUT = Path('/tmp/s9_007')
OUT.mkdir(exist_ok=True)

PRE = '''import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_007')
import h, pandas as pd

u = h.t111()
don, ct, sp, kh, tt = u['don'], u['ct'], u['sp'], u['kh'], u['tt']
ok = don['st_norm'] == 'ok'


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def r2(x):
    return Decimal(str(float(x))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def ids_of(mask):
    return set(don.loc[mask, 'Mã chứng từ'])


def lines_in(mask):
    return ct[ct['Ma don'].isin(ids_of(mask))]


def revenue(mask):
    return float(lines_in(mask)['ttien'].sum())


def day_mask(day):
    d = pd.Timestamp(day)
    return (don['dt'] >= d) & (don['dt'] < d + pd.Timedelta(days=1))


def qty_of_size(y, m, size):
    sub = lines_in(ok & h.month_mask(don['dt'], y, m)).merge(
        sp[['SKU', 'size']], left_on='ID SP', right_on='SKU')
    sub = sub[(sub['size'] == size) & (sub['Đơn vị (tính)'] == 'ly')]
    return r0(float(sub['slqd'].sum()))


def qty_of_product(y, m, name):
    sku = sp.loc[sp['name_n'] == h.norm(name), 'SKU'].iloc[0]
    sub = lines_in(ok & h.month_mask(don['dt'], y, m))
    return r0(float(sub.loc[sub['ID SP'] == sku, 'slqd'].sum()))


def repayments(start, end):
    credit = don[(don['Phương thức TT'].astype(str).str.strip() == 'debt') &
                 (don['st_norm'] != 'cancel')][['Mã chứng từ', 'dt']]
    q = tt.merge(credit, left_on='Số HĐ', right_on='Mã chứng từ')
    q = q[(q['dt_x'] >= pd.Timestamp(start)) & (q['dt_x'] < pd.Timestamp(end))]
    q = q[q['dt_x'].dt.normalize() > q['dt_y'].dt.normalize()]
    return r0(float(q['tien'].sum()))
'''

S = {}

S['q_4fc9e1ac67a8'] = '''
RESULT = r0(revenue(ok & h.month_mask(don['dt'], 2026, 3)))
'''

S['q_524ddde4b889'] = '''
RESULT = r0(revenue(ok & h.month_mask(don['dt'], 2025, 1)))
'''

S['q_527026b3e1fb'] = '''
sku = sp.loc[sp['name_n'] == h.norm('Espresso (single)'), 'SKU'].iloc[0]
day = pd.Timestamp('2025-01-11')
ids = ids_of(don['dt'].dt.normalize() == day)  # cancelled/returned lines still count for price
sub = ct[ct['Ma don'].isin(ids) & (ct['ID SP'] == sku)]
RESULT = r0(float(sub['gia'].iloc[0]))
'''

S['q_71274e80eec1'] = '''
RESULT = qty_of_size(2026, 5, 'L')
'''

S['q_7af25952261a'] = '''
RESULT = int(((don['st_norm'] == 'cancel') & h.month_mask(don['dt'], 2025, 9)).sum())
'''

S['q_834b9b6ff399'] = '''
m = ok & h.month_mask(don['dt'], 2025, 6)
n = int(m.sum())
RESULT = r0(revenue(m) / n) if n else 0
'''

S['q_838a6f2a3392'] = '''
RESULT = repayments('2026-08-01', '2026-08-20')
'''

S['q_83b6654830d3'] = '''
RESULT = r0(revenue(ok & day_mask('2025-08-13')))
'''

S['q_841d6a6359f9'] = '''
cur = revenue(ok & h.month_mask(don['dt'], 2026, 4))
prev = revenue(ok & h.month_mask(don['dt'], 2026, 3))
RESULT = f"{(r2((cur - prev) / prev * 100)):.2f}%"
'''

S['q_8923e2fd6815'] = '''
RESULT = int((ok & day_mask('2026-07-02')).sum())
'''

S['q_912a0c4e5b70'] = '''
RESULT = repayments('2025-07-01', '2025-08-01')
'''

S['q_9a4f10fb0f31'] = '''
sub = lines_in(ok & day_mask('2026-01-19'))
sub = sub[sub['Đơn vị (tính)'] == 'ly']
RESULT = r0(float(sub['slqd'].sum()))
'''

S['q_a251408eaaa3'] = '''
RESULT = r0(revenue(ok & day_mask('2025-04-26')))
'''

S['q_a4c169ab2814'] = '''
RESULT = qty_of_product(2025, 7, 'Sữa tươi trân châu đường đen (L)')
'''

S['q_ace184f51d99'] = '''
RESULT = int((ok & day_mask('2025-12-28')).sum())
'''

S['q_ae0df4a36ad5'] = '''
RESULT = qty_of_product(2025, 8, 'Sinh tố xoài (M)')
'''

S['q_b6bb52ac15af'] = '''
RESULT = qty_of_product(2025, 6, 'Espresso (double)')
'''

S['q_b8abcac3d506'] = '''
RESULT = int(((don['st_norm'] == 'cancel') & h.month_mask(don['dt'], 2025, 6)).sum())
'''

S['q_bc9c524d61dc'] = '''
RESULT = qty_of_size(2025, 10, 'M')
'''

S['q_c06b32744104'] = '''
RESULT = int((ok & day_mask('2025-10-30')).sum())
'''

S['q_cea423d7b2f3'] = '''
RESULT = repayments('2025-03-01', '2025-04-01')
'''

S['q_cecc13a33584'] = '''
RESULT = int(((don['st_norm'] == 'cancel') & h.month_mask(don['dt'], 2025, 2)).sum())
'''

S['q_d41265f537b7'] = '''
RESULT = qty_of_size(2025, 6, 'M')
'''

S['q_dc07e7478d91'] = '''
sub = lines_in(ok & h.month_mask(don['dt'], 2025, 2)).merge(
    sp[['SKU', 'Nhom hang']], left_on='ID SP', right_on='SKU')
sub = sub[sub['Nhom hang'].astype(str).str.strip().str.lower() == 'đá xay']
RESULT = r0(float(sub['ttien'].sum()))
'''

S['q_ebf569095b9f'] = '''
RESULT = r0(revenue(ok & h.month_mask(don['dt'], 2025, 6)))
'''

for qid, body in S.items():
    (OUT / f'{qid}.py').write_text(PRE + body)
print('wrote', len(S))
