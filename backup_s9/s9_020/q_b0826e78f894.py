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

RESULT = r0(H.product_qty(ct, '2026-03-01', '2026-03-31', 'Siro ho cảm Ích Nhi chai 90ml'))
