"""Generate solution files for batch retry9_018 (biz_118 + biz_121)."""
from pathlib import Path

OUT = Path('/tmp/s9_018')
OUT.mkdir(exist_ok=True)

PRE8 = '''import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_017')
import h118 as H
import pandas as pd

t = H.tables()
ct, sp, gh = t['ct'], t['sp'], t['gh']


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
    q = float(re.search(r'\\d+', str(row['Số lượng'])).group())
    factor = float(row['slqd']) / q if q else 1.0
    return r0(float(H.money(row['Đơn giá'])) / (factor if factor else 1.0))
'''

PRE21 = '''import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_018')
import h121 as H
import pandas as pd

t = H.tables()
ct = t['ct']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
'''

S = {}

S['q_8d1b1ea5a1f7'] = (PRE8, '''
RESULT = r0(H.unit_qty(ct, '2025-08-18', '2025-08-24', 'bình'))
''')

S['q_931d3dd05e61'] = (PRE8, '''
RESULT = H.delivery_trips(gh, '2025-08-01', '2025-08-31')
''')

S['q_9602e7257869'] = (PRE8, '''
RESULT = r0(H.avg_order(ct, '2026-04-27', '2026-05-03'))
''')

S['q_9c3a619c1b15'] = (PRE8, '''
RESULT = r0(H.avg_order(ct, '2026-03-01', '2026-03-31'))
''')

S['q_9f2b09a94359'] = (PRE8, '''
RESULT = r0(H.product_qty(ct, '2025-09-01', '2025-09-30', 'Bếp gas đôi Rinnai RV-375SW'))
''')

S['q_a32d5dc937a6'] = (PRE8, '''
RESULT = days_at_least('2025-09-01', '2025-09-30', 59000000)
''')

S['q_a34bafa0ccd7'] = (PRE8, '''
RESULT = r0(H.revenue(ct, '2026-05-01', '2026-05-31'))
''')

S['q_a8d6ce3ffc4e'] = (PRE8, '''
RESULT = H.cust_counts(ct, '2026-04-01', '2026-04-30', 4)
''')

S['q_a9090ef32085'] = (PRE8, '''
RESULT = r0(H.group_rev(ct, '2025-07-01', '2025-07-31', 'xi măng'))
''')

S['q_b04b25980e8c'] = (PRE8, '''
RESULT = r0(H.revenue(ct, '2025-03-07', '2025-04-05'))
''')

S['q_b12aefa3d5a5'] = (PRE8, '''
RESULT = H.n_orders(ct, '2026-01-08', '2026-01-08')
''')

S['q_b1e5fa402e61'] = (PRE8, '''
RESULT = r0(H.revenue(ct, '2025-12-18', '2026-01-16'))
''')

S['q_bf2a0fe75b1e'] = (PRE8, '''
RESULT = days_at_least('2026-01-01', '2026-01-31', 53000000)
''')

S['q_cb6f587f5401'] = (PRE8, '''
RESULT = r0(H.avg_order(ct, '2025-09-01', '2025-09-30'))
''')

S['q_ce1404304ab8'] = (PRE8, '''
RESULT = unit_price('2025-08-19', 'Xi măng INSEE Power-S bao 50kg')
''')

S['q_d0f64184b33b'] = (PRE8, '''
RESULT = H.stale_items(ct, '2026-02-17', '2026-02-23')
''')

S['q_d804a7c7f81c'] = (PRE8, '''
RESULT = r0(H.revenue(ct, '2025-09-01', '2025-09-30'))
''')

S['q_da831cd15032'] = (PRE8, '''
RESULT = H.delivery_trips(gh, '2025-02-01', '2025-02-28')
''')

S['q_db4cefc5f21d'] = (PRE8, '''
cur = H.revenue(ct, '2026-07-01', '2026-07-20')
prev = H.revenue(ct, '2026-06-01', '2026-06-20')
RESULT = f"{(cur / prev - 1) * 100:.2f}%"
''')

S['q_e51a6496ab23'] = (PRE8, '''
RESULT = r0(H.unit_qty(ct, '2025-11-20', '2025-11-26', 'cây'))
''')

S['q_ea0b48379de7'] = (PRE8, '''
RESULT = H.n_orders(ct, '2026-04-19', '2026-04-19')
''')

S['q_ea71163260ae'] = (PRE8, '''
RESULT = r0(H.revenue(ct, '2026-03-15', '2026-03-15'))
''')

S['q_ed21efdd6942'] = (PRE8, '''
RESULT = H.cust_counts(ct, '2025-12-01', '2025-12-31', 3)
''')

S['q_ed3ef76aa90c'] = (PRE8, '''
RESULT = r0(H.group_rev(ct, '2026-07-01', '2026-07-31', 'cát đá'))
''')

S['q_060bfbc2a7a5'] = (PRE21, '''
RESULT = r0(H.avg_order(ct, '2026-05-25', '2026-05-31'))
''')

for qid, (pre, body) in S.items():
    (OUT / f'{qid}.py').write_text(pre + body)
print('wrote', len(S))
