import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_018')
import h121 as H
import pandas as pd

t = H.tables()
ct = t['ct']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def orders_at_least(start, end, thr):
    r = H.order_rev(ct, start, end)
    return int((r >= thr).sum())

sub = ct[H.month_mask(ct['dt'], 2025, 7)]
st = sub.groupby('Mã đơn hàng')['st_norm'].first()
RESULT = f"{(st == 'cancel').mean() * 100:.2f}%"
