"""Generate solution files for batch retry9_016 (biz_117)."""
from pathlib import Path

OUT = Path('/tmp/s9_016')
OUT.mkdir(exist_ok=True)

PRE = '''import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_015')
import h117 as H
import pandas as pd

t = H.tables()
ct, gh, nh, ton, bang = t['ct'], t['gh'], t['nh'], t['ton'], t['bang']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def cust_counts(start, end, minn):
    sub = H.orders_in(ct, start, end)
    per = sub.groupby('Mã phiếu')['TenKH'].first().astype(str).map(H.norm)
    per = per[~per.isin(['khach le', 'le', 'kl', ''])]
    return int((per.value_counts() >= minn).sum())
'''

S = {}

S['q_55640348e6de'] = '''
RESULT = cust_counts('2026-01-01', '2026-01-31', 5)
'''

S['q_59beb968f122'] = '''
RESULT = r0(H.purchase_avg(nh, '2025-05-01', '2025-05-31', 'Thép Pomina D14 cây 11.7m', per_unit='cây'))
'''

S['q_5ade9d699c7f'] = '''
RESULT = r0(H.product_rev(ct, '2025-06-01', '2025-06-30', 'Thép Pomina D10 cây 11.7m'))
'''

S['q_607f89f0a1de'] = '''
RESULT = H.stale_items(ct, '2025-11-02', '2025-11-08')
'''

S['q_647f9a1e1d5a'] = '''
RESULT = r0(H.revenue(ct, '2025-01-01', '2025-01-31'))
'''

S['q_65c8757b42cc'] = '''
RESULT = H.delivery_trips(gh, '2025-09-01', '2025-09-30')
'''

S['q_65fe3145f067'] = '''
RESULT = H.stale_items(ct, '2025-01-31', '2025-02-06')
'''

S['q_6821f6e7e582'] = '''
RESULT = r0(H.revenue(ct, '2025-04-01', '2025-04-30'))
'''

S['q_700cb0d7392c'] = '''
RESULT = r0(H.purchase_cost(nh, '2026-02-01', '2026-02-28'))
'''

S['q_7d414ba60371'] = '''
RESULT = r0(H.purchase_cost(nh, '2025-04-01', '2025-04-30'))
'''

S['q_8e2acddfe818'] = '''
RESULT = r0(H.avg_order(ct, '2025-11-01', '2025-11-30'))
'''

S['q_8ee0c4a6c013'] = '''
RESULT = H.delivery_trips(gh, '2026-03-01', '2026-03-31')
'''

S['q_8faae2f5f17e'] = '''
RESULT = r0(H.avg_order(ct, '2026-03-02', '2026-03-08'))
'''

S['q_8fb58ebe7913'] = '''
RESULT = r0(H.avg_order(ct, '2026-02-01', '2026-02-28'))
'''

S['q_936fd5dcdc0c'] = '''
row = ton[ton['name_n'] == H.norm('Gas Saigon Petro 12kg')]
RESULT = int(round(float(row['ton'].iloc[0])))
'''

S['q_a50a68e0fcf0'] = '''
RESULT = H.stale_items(ct, '2026-02-09', '2026-02-15')
'''

S['q_a8c6117d3679'] = '''
RESULT = int(round(H.product_qty(ct, '2026-02-01', '2026-02-28', 'Thép Pomina D14 cây 11.7m')))
'''

S['q_acfac98021c8'] = '''
RESULT = r0(H.avg_order(ct, '2025-08-25', '2025-08-31'))
'''

S['q_b60ca2c9f083'] = '''
RESULT = H.delivery_trips(gh, '2025-07-01', '2025-07-31')
'''

S['q_bb84028b2a96'] = '''
RESULT = r0(H.purchase_avg(nh, '2026-01-01', '2026-01-31', 'Cát xây tô', per_unit='xe 4m3'))
'''

S['q_c4dadd843270'] = '''
RESULT = int(round(H.product_qty(ct, '2026-04-01', '2026-04-30', 'Máy bơm nước Panasonic GP-129JXK 125W')))
'''

S['q_d61bfdeb85ef'] = '''
RESULT = r0(H.revenue(ct, '2025-01-01', '2025-03-31'))
'''

S['q_d8aed0de270b'] = '''
r = H.order_rev(ct, '2025-05-01', '2025-05-31')
RESULT = int((r >= 1500000).sum())
'''

S['q_ddd4f8184ea7'] = '''
RESULT = r0(H.revenue(ct, '2025-09-01', '2025-09-07'))
'''

S['q_de9e64845a9f'] = '''
RESULT = r0(H.revenue(ct, '2025-06-01', '2025-06-30'))
'''

for qid, body in S.items():
    (OUT / f'{qid}.py').write_text(PRE + body)
print('wrote', len(S))
