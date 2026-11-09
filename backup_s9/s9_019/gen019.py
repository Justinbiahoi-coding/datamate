"""Generate solution files for batch retry9_019 (biz_121)."""
from pathlib import Path

OUT = Path('/tmp/s9_019')
OUT.mkdir(exist_ok=True)

PRE = '''import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_018')
import h121 as H
import pandas as pd

t = H.tables()
ct, sp, nct = t['ct'], t['sp'], t['nct']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def days_at_least(start, end, thr):
    sub = H.orders_in(ct, start, end)
    d = sub.groupby(sub['dt'].dt.normalize())['ttien'].sum()
    return int((d >= thr).sum())


def unit_price(day, name):
    d = pd.Timestamp(day)
    sub = ct[(ct['dt'].dt.normalize() == d) & (ct['name_n'] == H.norm(name))]
    row = sub.iloc[0]
    return r0(float(H.money(row['Giá sản phẩm'])) / float(row['factor'] or 1.0))


def orders_at_least(start, end, thr):
    r = H.order_rev(ct, start, end)
    return int((r >= thr).sum())
'''

S = {}

S['q_0d1d7ead3e7e'] = '''
RESULT = r0(H.ingredient_rev(ct, '2026-09-01', '2026-09-30', 'Cetirizin'))
'''
S['q_15fd61233685'] = '''
RESULT = unit_price('2025-07-25', 'Otrivin 0,1% xịt mũi chai 10ml')
'''
S['q_17b17408d4cc'] = '''
RESULT = r0(H.revenue(ct, '2026-06-01', '2026-06-30'))
'''
S['q_1d614f702a45'] = '''
RESULT = H.n_orders(ct, '2025-11-24', '2025-11-26')
'''
S['q_22a623d3df73'] = '''
RESULT = r0(H.rx_rev(ct, '2026-03-01', '2026-03-31', False))
'''
S['q_260318057077'] = '''
RESULT = r0(H.revenue(ct, '2026-04-01', '2026-06-30'))
'''
S['q_2695b1aade24'] = '''
RESULT = r0(H.product_qty(ct, '2026-02-01', '2026-02-28', 'Siro ho Bổ phế Nam Hà Chỉ Khái Lộ chai 125ml'))
'''
S['q_27e70e72d2dc'] = '''
RESULT = r0(H.ingredient_rev(ct, '2025-04-01', '2025-04-30', 'Paracetamol + Phenylephrin + Clorpheniramin'))
'''
S['q_2bad0a17ac14'] = '''
RESULT = r0(H.group_rev(ct, '2025-11-01', '2025-11-30', 'ho cảm cúm'))
'''
S['q_3d7beff53344'] = '''
RESULT = r0(H.revenue(ct, '2026-01-01', '2026-04-13'))
'''
S['q_3fb8f1a66d86'] = '''
RESULT = r0(H.revenue(ct, '2026-04-01', '2026-04-30'))
'''
S['q_4ac933ecda53'] = '''
RESULT = int(round(H.stock_now(ct, nct, 'V.Rohto Vitamin nhỏ mắt lọ 13ml')))
'''
S['q_57cf71f4503a'] = '''
RESULT = r0(H.rx_rev(ct, '2026-09-01', '2026-09-30', False))
'''
S['q_788ba58564e4'] = '''
RESULT = H.cust_counts(ct, '2025-08-01', '2025-08-31', 6)
'''
S['q_7b81f86b8409'] = '''
RESULT = r0(H.ingredient_rev(ct, '2025-04-01', '2025-04-30', 'Paracetamol'))
'''
S['q_8a434f1ff0e2'] = '''
RESULT = r0(H.avg_order(ct, '2025-07-07', '2025-07-13'))
'''
S['q_981e73d98b8d'] = '''
RESULT = r0(H.revenue(ct, '2026-01-01', '2026-06-05'))
'''
S['q_9ad226a1d120'] = '''
RESULT = days_at_least('2025-09-01', '2025-09-30', 7900000)
'''
S['q_9c65a0887f5b'] = '''
RESULT = r0(H.revenue(ct, '2025-05-05', '2025-05-10'))
'''
S['q_a2dca8d2acc3'] = '''
RESULT = orders_at_least('2025-05-01', '2025-05-31', 42000)
'''
S['q_a40aa0aa5714'] = '''
RESULT = r0(H.ingredient_rev(ct, '2026-09-01', '2026-09-30', 'Paracetamol + Phenylephrin + Clorpheniramin'))
'''
S['q_a57e54686875'] = '''
RESULT = r0(H.revenue(ct, '2026-05-17', '2026-06-15'))
'''
S['q_a6db6ea82b1e'] = '''
RESULT = r0(H.revenue(ct, '2025-07-28', '2025-08-03'))
'''
S['q_ac502a99776e'] = '''
RESULT = orders_at_least('2026-04-01', '2026-04-30', 130000)
'''
S['q_aee7f655095b'] = '''
RESULT = r0(H.avg_order(ct, '2025-05-12', '2025-05-18'))
'''

for qid, body in S.items():
    (OUT / f'{qid}.py').write_text(PRE + body)
print('wrote', len(S))
