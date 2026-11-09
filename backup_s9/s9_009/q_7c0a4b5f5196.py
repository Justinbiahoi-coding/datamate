import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_009')
import h112 as H
import pandas as pd

t = H.tables()
ct, sp = t['ct'], t['sp']
ok = ct['st_norm'] == 'ok'


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def day_range(start, end):
    s = pd.Timestamp(start)
    e = pd.Timestamp(end) + pd.Timedelta(days=1)
    return ok & (ct['dt'] >= s) & (ct['dt'] < e)


def month_lines(y, m):
    return ct[ok & H.month_mask(ct['dt'], y, m)]


def revenue(mask):
    return float(ct.loc[mask, 'ttien'].sum())


def order_revenue(y, m=None):
    sub = ct[ok & (H.month_mask(ct['dt'], y, m) if m else pd.Series(True, index=ct.index))]
    return sub.groupby('Mã đơn hàng')['ttien'].sum()


def last_week(as_of):
    d = pd.Timestamp(as_of)
    mon = d - pd.Timedelta(days=d.dayofweek)
    return mon - pd.Timedelta(days=7), mon - pd.Timedelta(days=1)


def qty_size(y, m, size):
    return r0(H.size_qty(ct, y, m, size))


def qty_product(y, m, name):
    return r0(H.product_qty(ct, y, m, name))


def group_rev(y, m, group):
    return r0(H.group_rev(ct, y, m, group))


def prod_rev(y, m, name):
    return r0(H.product_rev(ct, y, m, name))

sub = month_lines(2026, 5)
daily = sub.groupby(sub['dt'].dt.normalize())['ttien'].sum()
RESULT = int((daily >= 11_000_000).sum())
