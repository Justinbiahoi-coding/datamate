import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_017')
import h118 as H
import pandas as pd

t = H.tables()
ct, sp, gh = t['ct'], t['sp'], t['gh']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

sub = H.orders_in(ct, '2025-08-01', '2025-08-31')
per = sub.groupby('name_n')['Mã đơn hàng'].nunique()
RESULT = int((per >= 64).sum())
