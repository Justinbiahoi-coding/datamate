"""Generate solution files for batch retry9_021 (biz_123)."""
from pathlib import Path

OUT = Path('/tmp/s9_021')
OUT.mkdir(exist_ok=True)

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

S['q_43bd6fa219e8'] = '''
od = debt_orders('2025-06-21')
RESULT = int(od['MaKhachHang'].dropna().nunique())
'''
S['q_498456d33c36'] = '''
RESULT = r0(H.purchase_avg(ctn, 'Phosphalugel hộp 26 gói', '2025-09-01', '2025-09-30', per_unit='hộp'))
'''
S['q_4a7753540dbd'] = '''
RESULT = r0(H.purchase_avg(ctn, 'Panadol Extra hộp 15 vỉ x 12 viên', '2026-04-01', '2026-04-30', per_unit='hộp'))
'''
S['q_4b0716e646ec'] = '''
RESULT = r0(H.revenue(ct, dh, '2025-12-01', '2025-12-31'))
'''
S['q_4db85350a07d'] = '''
RESULT = r0(H.group_rev(ct, dh, '2025-06-01', '2025-06-30', 'vitamin khoáng chất'))
'''
S['q_5555b4641883'] = '''
RESULT = r0(H.revenue(ct, dh, '2025-06-01', '2025-06-30'))
'''
S['q_5a06c0d6b43f'] = '''
RESULT = r0(float(debt_orders('2026-03-29')['out'].sum()))
'''
S['q_732f3ccfba93'] = '''
RESULT = r0(H.rx_rev(ct, dh, '2025-08-01', '2025-08-31', True))
'''
S['q_73d56125b82b'] = '''
RESULT = collections('2025-07-01', '2025-07-31')
'''
S['q_7eb3c9221014'] = '''
RESULT = collections('2025-02-01', '2025-02-28')
'''
S['q_814a5d922a52'] = '''
RESULT = r0(H.avg_order(ct, dh, '2025-02-01', '2025-02-28'))
'''
S['q_86b7c3a59d4f'] = '''
RESULT = r0(H.avg_order(ct, dh, '2025-09-01', '2025-09-30'))
'''
S['q_8837ab1dae97'] = '''
RESULT = r0(H.revenue(ct, dh, '2025-01-01', '2025-08-21'))
'''
S['q_8e3a17631a81'] = '''
RESULT = r0(H.avg_order(ct, dh, '2025-03-01', '2025-03-31'))
'''
S['q_8f5d3341ad12'] = '''
RESULT = H.n_orders(dh, '2025-06-14', '2025-07-13')
'''
S['q_95d57f989168'] = '''
RESULT = r0(H.group_rev(ct, dh, '2025-04-01', '2025-04-30', 'vitamin khoáng chất'))
'''
S['q_97b3f5b2c64e'] = '''
RESULT = r0(H.purchase_avg(ctn, 'Zyrtec 10mg hộp 1 vỉ x 10 viên', '2025-08-01', '2025-08-31', per_unit='hộp'))
'''
S['q_982aa369c047'] = '''
RESULT = r0(H.revenue(ct, dh, '2025-09-01', '2025-09-30'))
'''
S['q_9cb660902981'] = '''
RESULT = r0(H.ingredient_rev(ct, dh, '2026-06-01', '2026-06-30', 'Cetirizin'))
'''
S['q_9ffe32ff8c39'] = '''
RESULT = r0(H.purchase_avg(ctn, 'Biosubtyl-II hộp 25 gói', '2025-01-01', '2025-01-31', per_unit='hộp'))
'''
S['q_a666a74dcbea'] = '''
lo = H.load_business(H.ROOT / 'train' / 'data' / 'biz_123')['lo_hang'].copy()
dl = H.load_business(H.ROOT / 'train' / 'data' / 'biz_123')['chi_tiet_don_lo'].copy()
dl['s'] = pd.to_numeric(dl['SLQuyDoi'], errors='coerce').fillna(0)
dl['r'] = pd.to_numeric(dl['SLTraQuyDoi'], errors='coerce').fillna(0)
lo['s'] = lo['MaLo'].map(dl.groupby('MaLo')['s'].sum()).fillna(0)
lo['r'] = lo['MaLo'].map(dl.groupby('MaLo')['r'].sum()).fillna(0)
lo['remain'] = pd.to_numeric(lo['SLNhapQuyDoi'], errors='coerce') - lo['s'] + lo['r']
lo['hsd'] = pd.to_datetime(lo['HanSuDung'], errors='coerce')
win = lo[(lo['remain'] > 0) & (lo['hsd'] >= pd.Timestamp('2026-06-28')) & (lo['hsd'] <= pd.Timestamp('2026-09-26'))]
RESULT = int(win['MaHangHoa'].nunique())
'''
S['q_a72c4fccfdbd'] = '''
name = H.norm('Telfast HD 180mg hộp 3 vỉ x 10 viên')
ids = set(H.orders_in(dh, '2025-03-01', '2025-03-31')['MaHoaDon'])
sold = float(pd.to_numeric(ct[ct['MaHoaDon'].isin(ids) & (ct['name_n'] == name)]['SLQuyDoi'], errors='coerce').sum())
purch = float(ctn[(ctn['dt'] >= pd.Timestamp('2025-03-01')) & (ctn['dt'] < pd.Timestamp('2025-04-01'))
                  & (ctn['name_n'] == name)]['base_qty'].sum())
RESULT = r0(purch - sold)
'''
S['q_acb083a1be85'] = '''
RESULT = r0(H.revenue(ct, dh, '2025-11-01', '2025-11-30'))
'''
S['q_aff1f9ce5753'] = '''
RESULT = r0(H.cust_type_rev(ct, dh, '2026-06-01', '2026-06-30', 'sỉ'))
'''
S['q_b9b3bd170cef'] = '''
RESULT = r0(H.rx_rev(ct, dh, '2025-01-01', '2025-01-31', False))
'''

for qid, body in S.items():
    (OUT / f'{qid}.py').write_text(PRE + body)
print('wrote', len(S))
