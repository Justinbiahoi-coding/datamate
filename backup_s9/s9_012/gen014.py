"""Generate solution files for batch retry9_014."""
from pathlib import Path

OUT = Path('/tmp/s9_012')
OUT.mkdir(exist_ok=True)

PRE = '''import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_012')
import h116 as H
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

S = {}

S['q_13cac41b4c0a'] = '''
RESULT = orders(day_mask(pd.Timestamp('2026-03-29') - pd.Timedelta(days=1)))
'''
S['q_1ab03eb1b95b'] = '''
RESULT = revenue(month_mask(2026, 4))
'''
S['q_1b118bb533ea'] = '''
RESULT = revenue(day_mask(pd.Timestamp('2026-04-21') - pd.Timedelta(days=1)))
'''
S['q_1fafcda3bc1d'] = '''
RESULT = r0(H.group_rev(ct, 2025, 7, 'xi măng'))
'''
S['q_28eade307fbe'] = '''
RESULT = revenue(day_mask(pd.Timestamp('2026-05-29') - pd.Timedelta(days=1)))
'''
S['q_2c2fdcb79780'] = '''
m = (ct['st_norm'] == 'cancel') & H.month_mask(ct['dt'], 2025, 10)
RESULT = orders(m)
'''
S['q_3234281bf31d'] = '''
m = (ct['st_norm'] == 'cancel') & H.month_mask(ct['dt'], 2026, 5)
RESULT = orders(m)
'''
S['q_379082485c68'] = '''
RESULT = unit_price('2026-05-09', 'Công tắc 1 chiều Panasonic Wide kèm mặt')
'''
S['q_3a34540528de'] = '''
RESULT = revenue(day_mask(pd.Timestamp('2025-07-17') - pd.Timedelta(days=1)))
'''
S['q_40c60df4f99d'] = '''
RESULT = orders(day_mask(pd.Timestamp('2026-08-03') - pd.Timedelta(days=1)))
'''
S['q_51963984e8da'] = '''
RESULT = r0(H.group_rev(ct, 2025, 11, 'sắt thép'))
'''
S['q_51df1d87d246'] = '''
RESULT = avg_order(month_mask(2026, 3))
'''
S['q_5d38f6a80d74'] = '''
RESULT = revenue(day_mask(pd.Timestamp('2026-07-06')))
'''
S['q_60bb26040492'] = '''
RESULT = H.stale_items(ct, '2025-11-29', '2025-12-05')
'''
S['q_60bba813896a'] = '''
RESULT = avg_order(month_mask(2026, 7))
'''
S['q_61cb72bdb033'] = '''
RESULT = unit_price('2025-12-15', 'Ống PVC Bình Minh D50 cây 4m')
'''
S['q_656d2c874794'] = '''
RESULT = orders(day_mask(pd.Timestamp('2025-10-08') - pd.Timedelta(days=1)))
'''
S['q_66ab3bea14e6'] = '''
RESULT = r0(H.product_rev(ct, 2025, 8, 'Ổ cắm đôi 3 chấu Panasonic Wide WEV1582SW'))
'''
S['q_6d104fcb4d0f'] = '''
RESULT = revenue(month_mask(2025, 7))
'''
S['q_6e80ad8859dc'] = '''
RESULT = int(round(H.product_qty(ct, '2026-04-01', '2026-04-30', 'Bồn nước inox Sơn Hà 1000L ngang')))
'''
S['q_75bd3efe8d90'] = '''
m = (ct['st_norm'] == 'cancel') & H.month_mask(ct['dt'], 2026, 1)
RESULT = orders(m)
'''
S['q_87e32bb779c7'] = '''
RESULT = revenue(month_mask(2026, 3))
'''
S['q_8aa3aaf65ac7'] = '''
RESULT = H.stale_items(ct, '2025-08-12', '2025-09-10')
'''
S['q_946553e545c6'] = '''
m = (ct['st_norm'] == 'cancel') & H.month_mask(ct['dt'], 2025, 8)
RESULT = orders(m)
'''
S['q_9c4f266c89b7'] = '''
RESULT = unit_price('2026-01-30', 'Bếp gas đôi Rinnai RV-375SW')
'''

for qid, body in S.items():
    (OUT / f'{qid}.py').write_text(PRE + body)
print('wrote', len(S))
