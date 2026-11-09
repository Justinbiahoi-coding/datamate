import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_020')
import h123 as H
import pandas as pd

t = H.tables()
dh, ct, sp, tk, ctn, tt, pn = t['dh'], t['ct'], t['sp'], t['tk'], t['ctn'], t['tt'], t['pn']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

sub = pn[(pn['dt'] >= pd.Timestamp('2025-06-01')) & (pn['dt'] < pd.Timestamp('2025-07-01'))]
RESULT = r0(float(sub['TongGiaTriNhap'].sum()))
