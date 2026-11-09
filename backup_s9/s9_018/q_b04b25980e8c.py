import sys, re
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
    q = float(re.search(r'\d+', str(row['Số lượng'])).group())
    factor = float(row['slqd']) / q if q else 1.0
    return r0(float(H.money(row['Đơn giá'])) / (factor if factor else 1.0))

RESULT = r0(H.revenue(ct, '2025-03-07', '2025-04-05'))
