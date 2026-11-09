import sys, re
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

m = (ct['st_norm'] == 'cancel') & H.month_mask(ct['dt'], 2025, 6)
RESULT = orders(m)
