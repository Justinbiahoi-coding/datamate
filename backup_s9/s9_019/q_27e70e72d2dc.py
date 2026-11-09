import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_018')
import h121 as H
import pandas as pd

t = H.tables()
ct, sp, nct = t['ct'], t['sp'], t['nct']


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
    return r0(float(H.money(row['Giá sản phẩm'])) / float(row['factor'] or 1.0))


def orders_at_least(start, end, thr):
    r = H.order_rev(ct, start, end)
    return int((r >= thr).sum())

RESULT = r0(H.ingredient_rev(ct, '2025-04-01', '2025-04-30', 'Paracetamol + Phenylephrin + Clorpheniramin'))
