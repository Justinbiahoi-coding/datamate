"""Generate solution files for batch retry9_013."""
from pathlib import Path

OUT = Path('/tmp/s9_012')
OUT.mkdir(exist_ok=True)

PRE115 = '''import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_012')
import h115 as H
import pandas as pd

t = H.tables()
ct, sp = t['ct'], t['sp']
ok = ct['st_norm'] == 'ok'


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


def sl_numeric(s):
    m = re.search(r'\\d+', str(s))
    return float(m.group()) if m else 1.0


def unit_price(day, name):
    d = pd.Timestamp(day)
    sub = ct[(ct['dt'].dt.normalize() == d) & (ct['name_n'] == H.norm(name))]
    row = sub.iloc[0]
    factor = float(row['slqd']) / sl_numeric(row['Số lượng'])
    return r0(float(H.money(row['Đơn giá'])) / (factor if factor else 1.0))
'''

PRE116 = '''import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_012')
import h116 as H
import pandas as pd

t = H.tables()
ct, sp = t['ct'], t['sp']
ok = ct['st_norm'] == 'ok'


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
'''

S = {}

# ── biz_115 ────────────────────────────────────────────────────────────────
S['q_9d008baac57b'] = ('115', '''
RESULT = avg_order(month_mask(2026, 3))
''')
S['q_a299aa3af73a'] = ('115', '''
RESULT = revenue(day_mask(pd.Timestamp('2025-07-06')))
''')
S['q_a425610f4ebe'] = ('115', '''
RESULT = revenue(month_mask(2025, 6))
''')
S['q_a480d0b518ee'] = ('115', '''
RESULT = revenue(ok & (ct['dt'] >= pd.Timestamp('2025-07-01')) & (ct['dt'] < pd.Timestamp('2025-10-01')))
''')
S['q_a521ddd46599'] = ('115', '''
RESULT = H.stale_items(ct, '2025-07-29', '2025-08-04')
''')
S['q_a662f4109fd1'] = ('115', '''
RESULT = revenue(day_mask(pd.Timestamp('2025-04-21') - pd.Timedelta(days=1)))
''')
S['q_ab53ef991019'] = ('115', '''
RESULT = orders(day_mask(pd.Timestamp('2026-01-24')))
''')
S['q_ac89d5a26986'] = ('115', '''
RESULT = int(round(H.product_qty(ct, '2025-09-01', '2025-09-30', 'Chống thấm Kova CT-11A tường 20kg')))
''')
S['q_ba6165e723a7'] = ('115', '''
RESULT = revenue(day_mask(pd.Timestamp('2025-08-05') - pd.Timedelta(days=1)))
''')
S['q_c19a5e52749f'] = ('115', '''
RESULT = avg_order(month_mask(2025, 2))
''')
S['q_c38b94c20695'] = ('115', '''
RESULT = revenue(month_mask(2025, 9))
''')
S['q_c6ed04cfa977'] = ('115', '''
RESULT = H.stale_items(ct, '2025-10-22', '2025-10-28')
''')
S['q_c7334bfc3a29'] = ('115', '''
RESULT = revenue(month_mask(2025, 5))
''')
S['q_c9193a5bc039'] = ('115', '''
RESULT = int(round(H.product_qty(ct, '2025-06-01', '2025-06-30', 'Kẽm buộc 1mm')))
''')
S['q_ccce4aa278a6'] = ('115', '''
RESULT = int(round(H.product_qty(ct, '2026-03-01', '2026-03-31', 'Keo dán gạch Weber.tai fix xám 25kg')))
''')
S['q_cdb758d4f7b8'] = ('115', '''
m = (ct['st_norm'] == 'cancel') & H.month_mask(ct['dt'], 2025, 8)
RESULT = orders(m)
''')
S['q_d2b32a2c57d8'] = ('115', '''
RESULT = r0(H.product_rev(ct, 2026, 2, 'Gas Petrolimex 12kg'))
''')
S['q_d43085fae456'] = ('115', '''
RESULT = revenue(month_mask(2025, 2))
''')
S['q_d538d96dbbfa'] = ('115', '''
RESULT = orders(ok & (ct['dt'] >= pd.Timestamp('2025-10-01')) & (ct['dt'] < pd.Timestamp('2026-01-01')))
''')
S['q_ddd87e1d24ed'] = ('115', '''
RESULT = H.stale_items(ct, '2025-10-07', '2025-10-13')
''')
S['q_f0f722cc7d6a'] = ('115', '''
RESULT = r0(H.product_rev(ct, 2025, 12, 'Công tắc 1 chiều Panasonic Wide kèm mặt'))
''')
S['q_f1a0aa1323c0'] = ('115', '''
RESULT = unit_price('2025-05-23', 'Nước tinh khiết Bidrico 20L')
''')
S['q_f4946d7eeb31'] = ('115', '''
RESULT = avg_order(month_mask(2026, 1))
''')
S['q_ff044c6f2f4e'] = ('115', '''
RESULT = avg_order(month_mask(2025, 9))
''')

# ── biz_116 ────────────────────────────────────────────────────────────────
S['q_0cad040011d1'] = ('116', '''
RESULT = r0(H.product_rev(ct, 2025, 7, 'Tôn lạnh Hoa Sen 0.4mm'))
''')

PRE = {'115': PRE115, '116': PRE116}
for qid, (v, body) in S.items():
    (OUT / f'{qid}.py').write_text(PRE[v] + body)
print('wrote', len(S))
