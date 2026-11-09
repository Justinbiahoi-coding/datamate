import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_022')
import h124 as H
import pandas as pd

t = H.tables()
hd, ct, hh, nh, tk, pt, kh = t['hd'], t['ct'], t['hh'], t['nh'], t['tk'], t['pt'], t['kh']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

r = H.order_rev(ct, hd, '2026-02-01', '2026-02-28')
days = hd.set_index('Order ID')['day']
rr = r.to_frame('rev')
rr['day'] = rr.index.map(days)
day_rev = rr.groupby('day')['rev'].sum()
RESULT = int((day_rev >= 15000000).sum())
