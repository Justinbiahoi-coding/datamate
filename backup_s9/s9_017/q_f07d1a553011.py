import sys, re
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

r = H.order_rev(ct, '2025-08-01', '2025-08-31')
RESULT = int((r >= 3300000).sum())
