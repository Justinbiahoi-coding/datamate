from pathlib import Path
OUT = Path('/tmp/s9_023'); OUT.mkdir(exist_ok=True)
PRE = '''import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_022')
import h124 as H
import pandas as pd

t = H.tables()
hd, ct, hh, nh, tk, pt, kh = t['hd'], t['ct'], t['hh'], t['nh'], t['tk'], t['pt'], t['kh']

import sys as _s
_s.path.insert(0, '/Users/buivanthien/Learn/zalo chelen/datamate/code')
from pathlib import Path as _P
from loader import load_business as _lb
_b = _lb(_P('/Users/buivanthien/Learn/zalo chelen/datamate/train/data/biz_124'))


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def chiphi():
    cp = _b['SoTay_ChiPhi'].copy()
    cp['dt'] = cp['Ngày chi'].map(H.to_date)
    cp['amt'] = cp['So tien'].map(H.money)
    return cp


def net_profit(y, m):
    s = pd.Timestamp(y, m, 1)
    e = s + pd.offsets.MonthBegin(1)
    ids = set(hd[hd['valid'] & (hd['dt'] >= s) & (hd['dt'] < e)]['Order ID'])
    sub = ct[ct['Mã giao dịch'].isin(ids)]
    rev = sub['rev'].sum()
    cost = (sub['cost'] * sub['slg']).sum()
    exp = chiphi()
    exp = exp[(exp['dt'] >= s) & (exp['dt'] < e)]['amt'].sum()
    return rev - cost - exp
'''
S = {}
S['q_756afdf869ce'] = '''
row = tk[tk['Hàng hóa'].map(H.norm) == H.norm('Plusssz Max Multivitamin viên sủi tuýp 20 viên')]
RESULT = r0(float(row['stock'].sum()))
'''
S['q_7aab9df093c7'] = '''
sub = nh[(nh['dt'] >= pd.Timestamp('2025-01-01')) & (nh['dt'] < pd.Timestamp('2025-02-01'))]
RESULT = r0(float(sub['line_amount'].sum()))
'''
S['q_7afd67bcbf1a'] = '''
RESULT = r0(H.ingredient_rev(ct, hd, '2026-03-01', '2026-03-31', 'Natri clorid'))
'''
S['q_7c22e1b7a383'] = '''
od = H.debt_orders(hd, pt, '2025-06-21')
RESULT = int(od['Mã KH mua'].dropna().nunique())
'''
S['q_7dae0d81eb69'] = '''
lo = _b['BanHang_LoHang'].copy()
bl = _b['BanHang_BanTheoLo'].copy()
lo['hsd'] = pd.to_datetime(lo['HSD'], errors='coerce', dayfirst=True)
lo['nhap'] = pd.to_numeric(lo['SL nhập (ĐVT cơ bản)'], errors='coerce')
bl['sold'] = pd.to_numeric(bl['SL quy ra lẻ'], errors='coerce')
bl['ret'] = pd.to_numeric(bl['SL trả (ĐVT cơ bản)'], errors='coerce')
lo['sold'] = lo['Lô'].map(bl.groupby('Lô')['sold'].sum()).fillna(0)
lo['ret'] = lo['Lô'].map(bl.groupby('Lô')['ret'].sum()).fillna(0)
lo['remain'] = lo['nhap'] - lo['sold'] + lo['ret']
win = lo[(lo['remain'] > 0.5) & (lo['hsd'] >= pd.Timestamp('2026-05-25')) & (lo['hsd'] <= pd.Timestamp('2026-09-22'))]
RESULT = int(len(win))
'''
S['q_83358960bf89'] = '''
sub = nh[(nh['dt'] >= pd.Timestamp('2026-03-01')) & (nh['dt'] < pd.Timestamp('2026-04-01'))]
RESULT = r0(float(sub['line_amount'].sum()))
'''
S['q_9960c0b5773f'] = '''
a = H.revenue(ct, hd, '2026-01-01', '2026-01-04')
b = H.revenue(ct, hd, '2025-12-01', '2025-12-04')
RESULT = f"{(a / b - 1) * 100:.2f}%"
'''
S['q_9a9a883e3a2f'] = '''
od = H.debt_orders(hd, pt, '2026-03-04')
RESULT = int(od['Mã KH mua'].dropna().nunique())
'''
S['q_9f9f075f0959'] = '''
RESULT = r0(H.revenue(ct, hd, '2025-04-01', '2025-04-30'))
'''
S['q_a149a00151dd'] = '''
RESULT = r0(net_profit(2025, 6))
'''
S['q_a527a825bbcb'] = '''
RESULT = r0(H.ingredient_rev(ct, hd, '2025-06-01', '2025-06-30', 'Loratadin'))
'''
S['q_b36894458481'] = '''
od = H.debt_orders(hd, pt, '2025-12-11')
RESULT = int(od['Mã KH mua'].dropna().nunique())
'''
S['q_b7846d205f52'] = '''
RESULT = r0(H.rx_rev(ct, hd, '2025-09-01', '2025-09-30', False))
'''
S['q_c2d367ddde3f'] = '''
RESULT = r0(net_profit(2025, 7))
'''
S['q_c3a500850ebb'] = '''
RESULT = r0(H.revenue(ct, hd, '2025-09-25', '2025-09-25'))
'''
S['q_c92029edd054'] = '''
name = 'Salonpas cao dán hộp 24 gói x 10 miếng'
sub = nh[(nh['name_n'] == H.norm(name)) & (nh['dt'] >= pd.Timestamp('2025-03-01')) & (nh['dt'] < pd.Timestamp('2025-04-01'))]
q = sub['qty'].sum()
RESULT = r0(float(sub['line_amount'].sum()) / q) if q else 0
'''
S['q_cb717b3a7e7c'] = '''
ids = set(H.orders_in(hd, '2025-06-01', '2025-06-30')['Order ID'])
s = hd[hd['Order ID'].isin(ids) & (hd['cust_rank'] == H.norm('thân thiết'))]
r = ct[ct['Mã giao dịch'].isin(set(s['Order ID']))].groupby('Mã giao dịch')['rev'].sum()
RESULT = r0(float(r.sum()) / r.size) if r.size else 0
'''
S['q_cc43ea1f6dcc'] = '''
od = H.debt_orders(hd, pt, '2025-06-28')
RESULT = int(od['Mã KH mua'].dropna().nunique())
'''
S['q_d99a85034d64'] = '''
name = 'Smecta hộp 30 gói'
sub = nh[(nh['name_n'] == H.norm(name)) & (nh['dt'] >= pd.Timestamp('2026-04-01')) & (nh['dt'] < pd.Timestamp('2026-05-01'))]
purch = float(sub['base_qty'].sum())
sold = H.product_qty(ct, hd, '2026-04-01', '2026-04-30', name)
RESULT = r0(purch - sold)
'''
S['q_e2a62a50df81'] = '''
RESULT = r0(H.rank_rev(ct, hd, '2025-04-01', '2025-04-30', 'sỉ'))
'''
S['q_eaf0d3e319f0'] = '''
name = 'Siro ăn ngon Ích Nhi Plus chai 100ml'
lsg = _b['BanHang_LichSuGia'].copy()
spid = hh[hh['Món'].map(H.norm) == H.norm(name)]['ma_sp'].iloc[0]
h = lsg[(lsg['Mã sản phẩm'] == spid) & (pd.to_datetime(lsg['Ngày áp dụng'], errors='coerce') <= pd.Timestamp('2025-08-09'))]
h = h.sort_values(pd.to_datetime(h['Ngày áp dụng'], errors='coerce'))
RESULT = r0(float(h['Giá mới'].iloc[-1]))
'''
S['q_fe8f9e79f8b5'] = '''
RESULT = r0(H.rx_rev(ct, hd, '2026-04-01', '2026-04-30', False))
'''
for q, b in S.items():
    (OUT / f'{q}.py').write_text(PRE + b)
print('wrote', len(S))
