import sys, re
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

RESULT = r0(H.purchase_avg(ctn, 'Panadol Extra hộp 15 vỉ x 12 viên', '2026-04-01', '2026-04-30', per_unit='hộp'))
