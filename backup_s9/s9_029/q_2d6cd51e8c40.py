import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_029')
import h130 as H
import pandas as pd

t = H.tables()
v = t['v']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
s = H.orders_in(v, '2025-07-01', '2025-07-31')
cnt = s.groupby('name_n')['Mã đơn hàng'].nunique()
RESULT = int((cnt >= 202).sum())
