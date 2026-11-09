from pathlib import Path
OUT = Path('/tmp/s9_022'); OUT.mkdir(exist_ok=True)
PRE = '''import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_020')
import h123 as H
import pandas as pd

t = H.tables()
dh, ct, sp, tk, ctn, tt, pn = t['dh'], t['ct'], t['sp'], t['tk'], t['ctn'], t['tt'], t['pn']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def debt_orders(asof):
    a = pd.Timestamp(asof) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    d = dh[(dh['TinhTrang'] != 'cancelled') & (dh['dt'] <= a) & (dh['PhuongThucTT'] != 'cod')].copy()
    paid = tt[tt['dt'] <= a].groupby('MaHoaDon')['SoTienThu'].sum()
    d['paid'] = d['MaHoaDon'].map(paid).fillna(0)
    d['out'] = d['TongThanhToan'] - d['paid']
    return d[d['out'] > 0]


def collections(start, end):
    m = tt.merge(dh[['MaHoaDon', 'dt', 'PhuongThucTT', 'TinhTrang']], on='MaHoaDon', suffixes=('', '_o'))
    m['lag'] = (m['dt'].dt.normalize() - m['dt_o'].dt.normalize()).dt.days
    s = m[(m['dt'] >= pd.Timestamp(start)) & (m['dt'] < pd.Timestamp(end) + pd.Timedelta(days=1))
          & (m['PhuongThucTT'] == 'debt') & (m['lag'] > 0) & (m['TinhTrang'] != 'cancelled')]
    return r0(float(s['SoTienThu'].sum()))
'''
S = {}
S['q_c42e3f58a010'] = '''
RESULT = collections('2026-03-01', '2026-03-31')
'''
S['q_cdaab312370d'] = '''
rx = H.rx_rev(ct, dh, '2025-09-01', '2025-09-30', True)
rev = H.revenue(ct, dh, '2025-09-01', '2025-09-30')
RESULT = f"{rx / rev * 100:.2f}%"
'''
S['q_cf239556b57d'] = '''
RESULT = r0(float(debt_orders('2026-06-28')['out'].sum()))
'''
S['q_d292d32fdf99'] = '''
d = dh[(dh['TinhTrang'] == 'cancelled') & (dh['dt'] >= pd.Timestamp('2026-01-01')) & (dh['dt'] < pd.Timestamp('2026-02-01'))]
RESULT = int(d['MaHoaDon'].nunique())
'''
S['q_d70531d80ed2'] = '''
RESULT = r0(H.ingredient_rev(ct, dh, '2025-12-01', '2025-12-31', 'Ibuprofen'))
'''
S['q_ffbb247c3151'] = '''
dh['shift'] = dh['MaCaLam'].astype(str).str[-1]
sub = dh[dh['valid'] & (dh['dt'] >= pd.Timestamp('2025-06-16')) & (dh['dt'] < pd.Timestamp('2025-06-23'))]
RESULT = int((sub['shift'] == '2').sum())
'''
for q, b in S.items():
    (OUT / f'{q}.py').write_text(PRE + b)
print('wrote', len(S))
