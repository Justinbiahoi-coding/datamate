import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_025')
import h126 as H

v = H.tables()['v']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
RESULT = r0(H.rev(v, '2025-11-01', '2025-11-01'))
