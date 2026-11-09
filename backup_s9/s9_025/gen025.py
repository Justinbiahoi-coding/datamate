from pathlib import Path
OUT = Path('/tmp/s9_025'); OUT.mkdir(exist_ok=True)
PRE126 = '''import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_025')
import h126 as H

v = H.tables()['v']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
'''
PRE127 = '''import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_025')
import h127 as H
import pandas as pd

t = H.tables()
dh, ct, tt, sp = t['dh'], t['ct'], t['tt'], t['sp']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
'''
A = {}
A['q_a5dfdc133c13'] = "RESULT = r0(H.rev(v, '2025-09-19', '2025-09-19'))\n"
A['q_af1ea83ef086'] = "RESULT = r0(H.rev(v, '2026-01-01', '2026-01-31'))\n"
A['q_b2c4cf5e2a8f'] = "RESULT = r0(H.qty(v, 'Bò lá lốt nướng', '2025-02-01', '2025-02-28'))\n"
A['q_b2cbd2b86b7d'] = "RESULT = r0(H.rev(v, '2025-11-01', '2025-11-01'))\n"
A['q_b57ac2eb26e0'] = "RESULT = r0(H.rev(v, '2025-10-01', '2025-12-31'))\n"
A['q_e2d8f7ac70bb'] = "RESULT = r0(H.qty(v, 'Gỏi bò bóp thấu', '2025-12-01', '2025-12-31'))\n"
A['q_eff8c82894a7'] = "RESULT = r0(H.rev(v, '2025-07-01', '2025-07-31'))\n"
A['q_f3b96d3fa415'] = "RESULT = r0(H.rev(v, '2026-01-11', '2026-01-11'))\n"
A['q_f7e4151bca71'] = "RESULT = r0(H.rev(v, '2026-03-07', '2026-03-07'))\n"
for q, b in A.items():
    (OUT / f'{q}.py').write_text(PRE126 + b)

B = {}
B['q_0285dfd1bb28'] = "RESULT = r0(H.avg_order(ct, dh, '2025-03-01', '2025-03-31'))\n"
B['q_044a0d4c3ff0'] = "RESULT = r0(H.qrev(ct, dh, '2025-09-01', '2025-09-30', 'Má heo nướng nước mắm'))\n"
B['q_091e0b747980'] = "RESULT = r0(H.revenue(ct, dh, '2026-04-01', '2026-06-30'))\n"
B['q_117496103d90'] = "RESULT = r0(H.qrev(ct, dh, '2026-04-01', '2026-04-30', 'Nghêu hấp sả'))\n"
B['q_132add5002d2'] = "RESULT = r0(H.avg_order(ct, dh, '2026-06-01', '2026-06-30'))\n"
B['q_1442d195be9c'] = "RESULT = r0(H.revenue(ct, dh, '2026-01-01', '2026-03-31'))\n"
B['q_2061ad0e2567'] = "RESULT = r0(H.collections(dh, tt, '2025-10-01', '2025-10-31'))\n"
B['q_24d19f2124c6'] = "RESULT = H.cancelled_count(dh, '2025-10-01', '2025-10-31')\n"
B['q_3190321c17b8'] = "RESULT = H.cancelled_count(dh, '2026-01-01', '2026-01-31')\n"
B['q_3247704353ac'] = "RESULT = r0(H.collections(dh, tt, '2026-07-01', '2026-07-28'))\n"
B['q_3931e1b343ad'] = "RESULT = r0(H.avg_order(ct, dh, '2025-08-01', '2025-08-31'))\n"
B['q_3e2132787f3d'] = "RESULT = r0(H.avg_order(ct, dh, '2026-02-01', '2026-02-28'))\n"
B['q_405d1830714c'] = "RESULT = r0(H.qrev(ct, dh, '2026-04-01', '2026-04-30', 'Bò lá lốt nướng'))\n"
B['q_44e61088806a'] = "RESULT = r0(H.avg_order(ct, dh, '2026-03-01', '2026-03-31'))\n"
B['q_47b39d7277a7'] = "RESULT = r0(H.revenue(ct, dh, '2025-12-30', '2025-12-30'))\n"
B['q_4909c1c5b936'] = "RESULT = H.n_orders(dh, '2026-02-15', '2026-02-15')\n"
for q, b in B.items():
    (OUT / f'{q}.py').write_text(PRE127 + b)
print('wrote', len(A) + len(B))
