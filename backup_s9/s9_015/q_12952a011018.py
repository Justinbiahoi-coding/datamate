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

RESULT = r0(H.purchase_avg(nh, '2025-08-01', '2025-08-31', 'Thép Pomina D10 cây 11.7m', per_unit='cây'))
