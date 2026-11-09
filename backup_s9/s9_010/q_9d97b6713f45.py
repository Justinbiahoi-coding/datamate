import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_009')
import h112 as H
import pandas as pd

t = H.tables()
ct = t['ct']
ok = ct['st_norm'] == 'ok'


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def day_range(start, end):
    s = pd.Timestamp(start)
    e = pd.Timestamp(end) + pd.Timedelta(days=1)
    return ok & (ct['dt'] >= s) & (ct['dt'] < e)


def last_week(as_of):
    d = pd.Timestamp(as_of)
    mon = d - pd.Timedelta(days=d.dayofweek)
    return mon - pd.Timedelta(days=7), mon - pd.Timedelta(days=1)


def month_lines(y, m):
    return ct[ok & H.month_mask(ct['dt'], y, m)]


def revenue(mask):
    return float(ct.loc[mask, 'ttien'].sum())


def avg_order(mask):
    rev = revenue(mask)
    n = ct.loc[mask, 'Mã đơn hàng'].nunique()
    return r0(rev / n) if n else 0


def group_rev(y, m, group):
    return r0(H.group_rev(ct, y, m, group))


def qty_product(y, m, name):
    return r0(H.product_qty(ct, y, m, name))


def price_on(name, day):
    d = pd.Timestamp(day)
    sub = ct[(ct['name_n'] == H.norm(name)) & (ct['dt'].dt.normalize() == d)]
    return r0(float(sub['gia'].iloc[0]))

RESULT = r0(float(month_lines(2026, 6)['ttien'].sum()))
