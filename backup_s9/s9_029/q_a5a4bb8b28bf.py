import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_029')
import h130 as H
import pandas as pd

t = H.tables()
v = t['v']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
RESULT = r0(H.avg_order(v, '2025-10-27', '2025-11-02'))
