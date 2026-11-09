import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_027')
import h129 as H
import pandas as pd

t = H.tables()
dh, ct, tt, sp = t['dh'], t['ct'], t['tt'], t['sp']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
RESULT = r0(H.qrev(ct, dh, '2025-01-01', '2025-01-31', 'Chân gà nướng'))
