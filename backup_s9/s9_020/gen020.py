"""Generate solution files for batch retry9_020 (biz_121 + biz_123)."""
from pathlib import Path

OUT = Path('/tmp/s9_020')
OUT.mkdir(exist_ok=True)

PRE21 = '''import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_018')
import h121 as H
import pandas as pd

t = H.tables()
ct = t['ct']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def orders_at_least(start, end, thr):
    r = H.order_rev(ct, start, end)
    return int((r >= thr).sum())
'''

PRE23 = '''import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_020')
import h123 as H
import pandas as pd

t = H.tables()
dh, ct, sp, tk, ctn, tt, pn = t['dh'], t['ct'], t['sp'], t['tk'], t['ctn'], t['tt'], t['pn']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
'''

S = {}

# ── biz_121 ───────────────────────────────────────────────────────────────
S['q_afbd14ac29de'] = (PRE21, '''
RESULT = orders_at_least('2025-11-01', '2025-11-30', 290000)
''')
S['q_b0826e78f894'] = (PRE21, '''
RESULT = r0(H.product_qty(ct, '2026-03-01', '2026-03-31', 'Siro ho cảm Ích Nhi chai 90ml'))
''')
S['q_c2223c076460'] = (PRE21, '''
RESULT = r0(H.revenue(ct, '2025-12-21', '2026-01-19'))
''')
S['q_c310ea22d66d'] = (PRE21, '''
RESULT = r0(H.ingredient_rev(ct, '2025-06-01', '2025-06-30', 'Cetirizin'))
''')
S['q_cd78ecfafd5e'] = (PRE21, '''
a = H.product_qty(ct, '2025-11-22', '2025-11-28', 'Efferalgan 500mg viên sủi hộp 4 vỉ x 4 viên')
b = H.product_qty(ct, '2025-11-15', '2025-11-21', 'Efferalgan 500mg viên sủi hộp 4 vỉ x 4 viên')
RESULT = f"{(a / b - 1) * 100:.2f}%"
''')
S['q_da501a232d0c'] = (PRE21, '''
RESULT = r0(H.rx_rev(ct, '2025-09-01', '2025-09-30', True))
''')
S['q_dc3fd604782e'] = (PRE21, '''
RESULT = r0(H.revenue(ct, '2025-04-01', '2025-04-30'))
''')
S['q_deb535c9e0a8'] = (PRE21, '''
RESULT = r0(H.product_qty(ct, '2026-06-01', '2026-06-30', 'Kudos vitamin C 1000mg viên sủi tuýp 20 viên'))
''')
S['q_e4afc48f7cb0'] = (PRE21, '''
sub = ct[H.month_mask(ct['dt'], 2025, 7)]
st = sub.groupby('Mã đơn hàng')['st_norm'].first()
RESULT = f"{(st == 'cancel').mean() * 100:.2f}%"
''')
S['q_e5f51c796fd2'] = (PRE21, '''
RESULT = r0(H.avg_order(ct, '2026-09-07', '2026-09-13'))
''')
S['q_ec33e9c57c6e'] = (PRE21, '''
RESULT = r0(H.rx_rev(ct, '2026-02-01', '2026-02-28', False))
''')
S['q_ed7bfab7d354'] = (PRE21, '''
RESULT = r0(H.revenue(ct, '2025-07-01', '2025-07-31'))
''')
S['q_ee2a9e668ccc'] = (PRE21, '''
RESULT = r0(H.revenue(ct, '2025-03-01', '2025-03-31'))
''')
S['q_fc467aba968d'] = (PRE21, '''
RESULT = r0(H.avg_order(ct, '2025-06-02', '2025-06-08'))
''')

# ── biz_123 ───────────────────────────────────────────────────────────────
S['q_0a14fc442eee'] = (PRE23, '''
RESULT = r0(H.group_rev(ct, dh, '2025-12-01', '2025-12-31', 'giảm đau hạ sốt'))
''')
S['q_0bf0638eaa4d'] = (PRE23, '''
RESULT = r0(H.debt_at(dh, tt, '2026-05-15'))
''')
S['q_0c4f869d0e49'] = (PRE23, '''
RESULT = r0(H.rx_rev(ct, dh, '2025-11-01', '2025-11-30', True))
''')
S['q_12bcf28ac9f0'] = (PRE23, '''
RESULT = r0(H.employee_rev(ct, dh, '2026-01-01', '2026-01-31', 'NV003'))
''')
S['q_18e8c7f00fce'] = (PRE23, '''
RESULT = r0(H.debt_at(dh, tt, '2025-10-08', older_than=15))
''')
S['q_250cc0cd8ae0'] = (PRE23, '''
RESULT = H.orders_at_least(ct, dh, '2025-06-01', '2025-06-30', 41000)
''')
S['q_257bf10688b9'] = (PRE23, '''
RESULT = r0(H.cust_type_rev(ct, dh, '2025-12-01', '2025-12-31', 'sỉ'))
''')
S['q_2bd1825f38c7'] = (PRE23, '''
RESULT = r0(H.revenue(ct, dh, '2025-07-01', '2025-09-30'))
''')
S['q_334438589ac0'] = (PRE23, '''
sub = pn[(pn['dt'] >= pd.Timestamp('2025-06-01')) & (pn['dt'] < pd.Timestamp('2025-07-01'))]
RESULT = r0(float(sub['TongGiaTriNhap'].sum()))
''')
S['q_353b11adef47'] = (PRE23, '''
RESULT = r0(H.purchase_avg(ctn, 'Clorpheniramin 4mg DHG hộp 10 vỉ x 20 viên', '2025-01-01', '2025-01-31', per_unit='hộp'))
''')
S['q_42f55486f412'] = (PRE23, '''
RESULT = r0(H.inventory_value(ct, dh, tk, sp, '2026-06-28'))
''')

for qid, (pre, body) in S.items():
    (OUT / f'{qid}.py').write_text(pre + body)
print('wrote', len(S))
