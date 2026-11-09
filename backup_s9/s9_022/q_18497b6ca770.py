import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_022')
import h124 as H
import pandas as pd

t = H.tables()
hd, ct, hh, nh, tk, pt, kh = t['hd'], t['ct'], t['hh'], t['nh'], t['tk'], t['pt'], t['kh']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

sub = nh[(nh['dt'] >= pd.Timestamp('2025-02-01')) & (nh['dt'] < pd.Timestamp('2025-03-01'))]
RESULT = r0(float(sub['line_amount'].sum()))
