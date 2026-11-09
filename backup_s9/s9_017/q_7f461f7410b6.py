import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_017')
import h118 as H
import pandas as pd

t = H.tables()
ct, sp, gh = t['ct'], t['sp'], t['gh']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

RESULT = H.stale_items(ct, '2026-08-20', '2026-08-26')
