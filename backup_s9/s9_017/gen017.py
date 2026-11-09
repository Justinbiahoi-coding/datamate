"""Generate solution files for batch retry9_017 (biz_117 + biz_118)."""
from pathlib import Path

OUT = Path('/tmp/s9_017')
OUT.mkdir(exist_ok=True)

PRE7 = '''import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_015')
import h117 as H
import pandas as pd

t = H.tables()
ct, gh, nh, ton, bang = t['ct'], t['gh'], t['nh'], t['ton'], t['bang']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def price_on(day, name):
    row = bang[(bang['name_n'] == H.norm(name)) & (bang['dt'] <= pd.Timestamp(day))].sort_values('dt')
    return r0(float(row.iloc[-1]['gia_moi']))
'''

PRE8 = '''import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_017')
import h118 as H
import pandas as pd

t = H.tables()
ct, sp, gh = t['ct'], t['sp'], t['gh']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
'''

S = {}

# ── biz_117 ───────────────────────────────────────────────────────────────
S['q_e19e472cfafe'] = (PRE7, '''
RESULT = r0(H.product_rev(ct, '2025-12-01', '2025-12-31', 'Thép Pomina D12 cây 11.7m'))
''')

S['q_e35d8fac5233'] = (PRE7, '''
sub = H.orders_in(ct, '2026-01-01', '2026-01-31')
per = sub.groupby('Mã phiếu')['TenKH'].first().astype(str).map(H.norm)
per = per[~per.isin(['khach le', 'le', 'kl', ''])]
RESULT = int((per.value_counts() >= 3).sum())
''')

S['q_e48e9fb676f5'] = (PRE7, '''
RESULT = r0(H.product_rev(ct, '2025-07-01', '2025-07-31', 'Đá 1x2'))
''')

S['q_ed9ac953351f'] = (PRE7, '''
row = ton[ton['name_n'] == H.norm('Bột trét Jotun nội thất 40kg')]
RESULT = int(round(float(row['ton'].iloc[0])))
''')

S['q_f04f3cf741d6'] = (PRE7, '''
RESULT = r0(H.purchase_cost(nh, '2025-09-01', '2025-09-30'))
''')

S['q_f06ff238b76c'] = (PRE7, '''
RESULT = price_on('2025-06-21', 'Cát san lấp')
''')

S['q_f07d1a553011'] = (PRE7, '''
r = H.order_rev(ct, '2025-08-01', '2025-08-31')
RESULT = int((r >= 3300000).sum())
''')

S['q_f6e9d280f14b'] = (PRE7, '''
RESULT = r0(H.purchase_avg(nh, '2026-04-01', '2026-04-30', 'Nước kiềm Ion Life 19L'))
''')

S['q_f7a67bc6eecd'] = (PRE7, '''
RESULT = H.stale_items(ct, '2025-03-31', '2025-04-06')
''')

S['q_f7eb4c1dfb74'] = (PRE7, '''
RESULT = r0(H.revenue(ct, '2025-02-24', '2025-02-28'))
''')

S['q_fca74e8bad45'] = (PRE7, '''
RESULT = r0(H.revenue(ct, '2025-03-27', '2025-04-25'))
''')

# ── biz_118 ───────────────────────────────────────────────────────────────
S['q_03766ac30505'] = (PRE8, '''
RESULT = H.n_orders(ct, '2025-10-01', '2025-12-31')
''')

S['q_158b312e8f5b'] = (PRE8, '''
RESULT = r0(H.revenue(ct, '2025-06-01', '2025-06-30'))
''')

S['q_1ce591033a80'] = (PRE8, '''
RESULT = r0(H.product_rev(ct, '2026-08-01', '2026-08-31', 'Sơn Dulux Weathershield Powerflexx 5L'))
''')

S['q_2646a315a83f'] = (PRE8, '''
RESULT = r0(H.unit_qty(ct, '2026-08-03', '2026-08-09', 'm3'))
''')

S['q_3455f22dc8c4'] = (PRE8, '''
RESULT = r0(H.group_rev(ct, '2026-02-01', '2026-02-28', 'điện'))
''')

S['q_39769b4c6a4f'] = (PRE8, '''
RESULT = r0(H.revenue(ct, '2025-06-15', '2025-06-21'))
''')

S['q_40fb39cf0973'] = (PRE8, '''
RESULT = r0(H.avg_order(ct, '2026-07-01', '2026-07-31'))
''')

S['q_440545f5b178'] = (PRE8, '''
RESULT = H.delivery_trips(gh, '2025-07-01', '2025-07-31')
''')

S['q_7550b258098d'] = (PRE8, '''
RESULT = r0(H.revenue(ct, '2026-01-01', '2026-06-02'))
''')

S['q_7f461f7410b6'] = (PRE8, '''
RESULT = H.stale_items(ct, '2026-08-20', '2026-08-26')
''')

S['q_82b3c2df8baa'] = (PRE8, '''
RESULT = H.delivery_trips(gh, '2025-04-01', '2025-04-30')
''')

S['q_8a84b3d3341a'] = (PRE8, '''
sub = H.orders_in(ct, '2025-08-01', '2025-08-31')
per = sub.groupby('name_n')['Mã đơn hàng'].nunique()
RESULT = int((per >= 64).sum())
''')

S['q_8b26c18bfb11'] = (PRE8, '''
RESULT = H.cust_counts(ct, '2025-04-01', '2025-04-30', 4)
''')

S['q_8ba7aa8f4b8e'] = (PRE8, '''
RESULT = r0(H.revenue(ct, '2026-01-01', '2026-05-10'))
''')

for qid, (pre, body) in S.items():
    (OUT / f'{qid}.py').write_text(pre + body)
print('wrote', len(S))
