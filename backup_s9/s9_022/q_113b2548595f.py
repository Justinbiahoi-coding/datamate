import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_022')
import h124 as H
import pandas as pd

t = H.tables()
hd, ct, hh, nh, tk, pt, kh = t['hd'], t['ct'], t['hh'], t['nh'], t['tk'], t['pt'], t['kh']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

row = tk[tk['Hàng hóa'].map(H.norm) == H.norm('Bio-acimin Gold men vi sinh hộp 30 gói')]
RESULT = r0(float(row['stock'].sum()))
