import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_015')
import h117 as H
import pandas as pd

t = H.tables()
ct, gh, nh = t['ct'], t['gh'], t['nh']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def orders_between(start, end):
    return H.n_orders(ct, start, end)

sub = H.orders_in(ct, '2025-10-01', '2025-10-31')
per_cust = sub.groupby('Mã phiếu')['TenKH'].first().astype(str).map(H.norm)
cnt = per_cust[~per_cust.isin(['khach le', 'le', 'kl', ''])]

RESULT = int((cnt.value_counts() >= 4).sum())
