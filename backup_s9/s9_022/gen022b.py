from pathlib import Path
OUT = Path('/tmp/s9_022'); OUT.mkdir(exist_ok=True)
PRE = '''import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_022')
import h124 as H
import pandas as pd

t = H.tables()
hd, ct, hh, nh, tk, pt, kh = t['hd'], t['ct'], t['hh'], t['nh'], t['tk'], t['pt'], t['kh']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
'''
S = {}
S['q_00195e1e4049'] = '''
RESULT = r0(H.ingredient_rev(ct, hd, '2026-05-01', '2026-05-25', 'Natri clorid'))
'''
S['q_026fa17395ed'] = '''
RESULT = r0(float(H.debt_orders(hd, pt, '2026-05-25')['out'].sum()))
'''
S['q_07430abba07b'] = '''
RESULT = r0(H.product_qty(ct, hd, '2025-10-01', '2025-10-31', 'Zyrtec 10mg hộp 1 vỉ x 10 viên'))
'''
S['q_0f6233b739e9'] = '''
RESULT = r0(H.ingredient_rev(ct, hd, '2025-11-01', '2025-11-30', 'Natri clorid'))
'''
S['q_113b2548595f'] = '''
row = tk[tk['Hàng hóa'].map(H.norm) == H.norm('Bio-acimin Gold men vi sinh hộp 30 gói')]
RESULT = r0(float(row['stock'].sum()))
'''
S['q_1360a4b30c2c'] = '''
RESULT = H.orders_at_least(ct, hd, '2025-06-01', '2025-06-30', 270000)
'''
S['q_13abc6cf460f'] = '''
RESULT = r0(H.ingredient_rev(ct, hd, '2025-07-01', '2025-07-31', 'Paracetamol'))
'''
S['q_141b4202edf8'] = '''
RESULT = r0(H.employee_rev(ct, hd, '2026-02-01', '2026-02-28', 'NV001'))
'''
S['q_14693fd38657'] = '''
d = H.debt_orders(hd, pt, '2025-11-12')
RESULT = int(d['Mã KH mua'].dropna().nunique())
'''
S['q_18497b6ca770'] = '''
sub = nh[(nh['dt'] >= pd.Timestamp('2025-02-01')) & (nh['dt'] < pd.Timestamp('2025-03-01'))]
RESULT = r0(float(sub['line_amount'].sum()))
'''
S['q_20ef7fe8e588'] = '''
RESULT = r0(H.avg_order(ct, hd, '2025-02-01', '2025-02-28'))
'''
S['q_25c012ee0fce'] = '''
RESULT = r0(H.collections(hd, pt, '2025-08-01', '2025-08-31'))
'''
S['q_33a2f625cc8c'] = '''
RESULT = r0(H.revenue(ct, hd, '2025-05-01', '2025-05-31'))
'''
S['q_38472348f446'] = '''
RESULT = r0(H.group_rev(ct, hd, '2025-03-01', '2025-03-31', 'mắt mũi họng'))
'''
S['q_392694afa261'] = '''
RESULT = r0(H.avg_order(ct, hd, '2025-05-01', '2025-05-31'))
'''
S['q_4470cd3d68b2'] = '''
RESULT = H.n_orders(hd, '2025-01-01', '2025-05-08')
'''
S['q_5b1fc63aef42'] = '''
r = H.order_rev(ct, hd, '2026-02-01', '2026-02-28')
days = hd.set_index('Order ID')['day']
rr = r.to_frame('rev')
rr['day'] = rr.index.map(days)
day_rev = rr.groupby('day')['rev'].sum()
RESULT = int((day_rev >= 15000000).sum())
'''
S['q_64d1626a754c'] = '''
cost = hh.drop_duplicates('ma_sp').set_index('ma_sp')['Giá vốn hiện tại'].map(H.money)
RESULT = r0(float((tk['stock'] * tk['ID SP'].map(cost)).sum()))
'''
S['q_70212b454018'] = '''
RESULT = r0(H.rank_rev(ct, hd, '2025-08-01', '2025-08-31', 'sỉ'))
'''
for q, b in S.items():
    (OUT / f'{q}.py').write_text(PRE + b)
print('wrote', len(S))
