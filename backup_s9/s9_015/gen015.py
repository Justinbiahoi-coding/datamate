"""Generate solution files for batch retry9_015 (biz_116 + biz_117)."""
from pathlib import Path

OUT = Path('/tmp/s9_015')
OUT.mkdir(exist_ok=True)

PRE116 = '''import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_012')
import h116 as H
import pandas as pd

t = H.tables()
ct, sp = t['ct'], t['sp']
ok = ct['st_norm'] == 'ok'
unit_of = sp.drop_duplicates('name_n').set_index('name_n')['Đơn vị tính']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def day_mask(day):
    d = pd.Timestamp(day)
    return ok & (ct['dt'] >= d) & (ct['dt'] < d + pd.Timedelta(days=1))


def month_mask(y, m):
    return ok & H.month_mask(ct['dt'], y, m)


def revenue(mask):
    return r0(float(ct.loc[mask, 'ttien'].sum()))


def avg_order(mask):
    rev = float(ct.loc[mask, 'ttien'].sum())
    n = ct.loc[mask, 'Mã đơn hàng'].nunique()
    return r0(rev / n) if n else 0


def orders(mask):
    return int(ct.loc[mask, 'Mã đơn hàng'].nunique())
'''

PRE117 = '''import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_015')
import h117 as H
import pandas as pd

t = H.tables()
ct, gh, nh = t['ct'], t['gh'], t['nh']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def orders_between(start, end):
    return H.n_orders(ct, start, end)
'''

S = {}

# ── biz_116 ───────────────────────────────────────────────────────────────
S['q_9da820e20d62'] = (PRE116, '''
mask = day_mask(pd.Timestamp('2025-09-05') - pd.Timedelta(days=1))
mask = mask & (ct['name_n'].map(unit_of) == 'cây')
RESULT = r0(float(ct.loc[mask, 'slqd'].sum()))
''')

S['q_a261fd5dd101'] = (PRE116, '''
aug = float(ct.loc[month_mask(2025, 8), 'ttien'].sum())
jul = float(ct.loc[month_mask(2025, 7), 'ttien'].sum())
RESULT = f"{(aug / jul - 1) * 100:.2f}%"
''')

S['q_a7d7f67cdf23'] = (PRE116, '''
RESULT = H.stale_items(ct, '2026-02-15', '2026-02-21')
''')

S['q_afe257db30d1'] = (PRE116, '''
RESULT = int(round(H.product_qty(ct, '2025-10-01', '2025-10-31', 'Bồn nước inox Sơn Hà 1000L ngang')))
''')

S['q_b00295e95190'] = (PRE116, '''
m = (ct['st_norm'] == 'cancel') & H.month_mask(ct['dt'], 2025, 6)
RESULT = orders(m)
''')

S['q_b2ea104e22e6'] = (PRE116, '''
m = ok & (ct['dt'] >= pd.Timestamp('2026-04-01')) & (ct['dt'] < pd.Timestamp('2026-07-01'))
RESULT = orders(m)
''')

S['q_b9febb40e782'] = (PRE116, '''
RESULT = orders(day_mask('2025-10-28'))
''')

S['q_bafa5c2589c4'] = (PRE116, '''
RESULT = avg_order(month_mask(2026, 6))
''')

S['q_bd6fee4b2a4f'] = (PRE116, '''
RESULT = avg_order(month_mask(2025, 10))
''')

S['q_bfec45414252'] = (PRE116, '''
RESULT = H.stale_items(ct, '2025-10-07', '2025-10-13')
''')

S['q_c0bce6d2640a'] = (PRE116, '''
RESULT = revenue(month_mask(2026, 1))
''')

S['q_d56ec905a1e2'] = (PRE116, '''
RESULT = int(round(H.product_qty(ct, '2025-10-01', '2025-10-31', 'Thép Pomina D14 cây 11.7m')))
''')

S['q_db7482372998'] = (PRE116, '''
RESULT = revenue(month_mask(2026, 6))
''')

S['q_deb764b69a75'] = (PRE116, '''
m = (ct['st_norm'] == 'cancel') & H.month_mask(ct['dt'], 2026, 8)
RESULT = orders(m)
''')

S['q_eebca2d30be6'] = (PRE116, '''
RESULT = avg_order(month_mask(2025, 8))
''')

S['q_ef257d3c2ef4'] = (PRE116, '''
RESULT = r0(H.product_rev(ct, 2025, 9, 'Thép Pomina D16 cây 11.7m'))
''')

S['q_f8fbad01c2a6'] = (PRE116, '''
RESULT = int(round(H.product_qty(ct, '2025-09-01', '2025-09-30', 'Thép Pomina D14 cây 11.7m')))
''')

# ── biz_117 ───────────────────────────────────────────────────────────────
S['q_047586efd4bf'] = (PRE117, '''
RESULT = H.delivery_trips(gh, '2026-01-01', '2026-01-31')
''')

S['q_0f7a713a9a4e'] = (PRE117, '''
r = H.order_rev(ct, '2026-01-01', '2026-01-31')
RESULT = int((r >= 580000).sum())
''')

S['q_12952a011018'] = (PRE117, '''
RESULT = r0(H.purchase_avg(nh, '2025-08-01', '2025-08-31', 'Thép Pomina D10 cây 11.7m', per_unit='cây'))
''')

S['q_16001b7edc7b'] = (PRE117, '''
RESULT = r0(H.avg_order(ct, '2026-01-01', '2026-01-31'))
''')

S['q_18a4f2eb5280'] = (PRE117, '''
RESULT = r0(H.purchase_avg(nh, '2025-01-01', '2025-01-31', 'Băng keo điện Nano 20 yard', per_unit='cây'))
''')

S['q_3afd914e38c7'] = (PRE117, '''
RESULT = r0(H.revenue(ct, '2025-06-23', '2025-06-29'))
''')

S['q_4b77ed39a2ff'] = (PRE117, '''
sub = H.orders_in(ct, '2025-10-01', '2025-10-31')
per_cust = sub.groupby('Mã phiếu')['TenKH'].first().astype(str).map(H.norm)
cnt = per_cust[~per_cust.isin(['khach le', 'le', 'kl', ''])]

RESULT = int((cnt.value_counts() >= 4).sum())
''')

S['q_5161c6b90828'] = (PRE117, '''
RESULT = r0(H.avg_order(ct, '2025-12-15', '2025-12-21'))
''')

for qid, (pre, body) in S.items():
    (OUT / f'{qid}.py').write_text(pre + body)
print('wrote', len(S))
