import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_022')
import h124 as H
import pandas as pd

t = H.tables()
hd, ct, hh, nh, tk, pt, kh = t['hd'], t['ct'], t['hh'], t['nh'], t['tk'], t['pt'], t['kh']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

cost = hh.drop_duplicates('ma_sp').set_index('ma_sp')['Giá vốn hiện tại'].map(H.money)
RESULT = r0(float((tk['stock'] * tk['ID SP'].map(cost)).sum()))
