import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_029')
import h130 as H
import pandas as pd

t = H.tables()
v = t['v']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
RESULT = r0(H.price_on_day(v, 'Bia Tiger lon', '2025-03-01'))
