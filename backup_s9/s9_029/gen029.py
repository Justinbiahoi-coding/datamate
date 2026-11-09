from pathlib import Path
OUT = Path('/tmp/s9_029'); OUT.mkdir(exist_ok=True)
PRE = '''import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_029')
import h130 as H
import pandas as pd

t = H.tables()
v = t['v']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
'''
S = {
'q_2c03415e4415': "RESULT = H.n_orders(v, '2026-01-01', '2026-05-22')\n",
'q_2d6cd51e8c40': """s = H.orders_in(v, '2025-07-01', '2025-07-31')
cnt = s.groupby('name_n')['Mã đơn hàng'].nunique()
RESULT = int((cnt >= 202).sum())
""",
'q_387c0c5b5e48': "RESULT = r0(H.revenue(v, '2025-06-30', '2025-07-04'))\n",
'q_6e9a3164fe79': "RESULT = r0(H.revenue(v, '2026-06-01', '2026-06-30'))\n",
'q_73c8a2181513': "RESULT = r0(H.qty(v, '2025-09-01', '2025-09-30', 'Đậu que xào tỏi'))\n",
'q_78e736c63ef1': "RESULT = r0(H.price_on_day(v, 'Bia Tiger lon', '2025-03-01'))\n",
'q_79e183f9b54d': "RESULT = r0(H.revenue(v, '2026-01-01', '2026-07-22'))\n",
'q_8d8942df683c': "RESULT = r0(H.revenue(v, '2025-12-01', '2025-12-31'))\n",
'q_96a0e6654b16': "RESULT = r0(H.group_rev(v, '2026-06-01', '2026-06-30', 'cơm mì cháo'))\n",
'q_9d3e7adfc8c1': "RESULT = r0(H.price_on_day(v, 'Cá lóc nướng trui', '2025-06-12'))\n",
'q_a5a4bb8b28bf': "RESULT = r0(H.avg_order(v, '2025-10-27', '2025-11-02'))\n",
'q_a7b6ac2570af': "RESULT = r0(H.avg_order(v, '2026-06-01', '2026-06-30'))\n",
'q_aae0b8869b67': "RESULT = r0(H.revenue(v, '2025-10-08', '2025-10-14'))\n",
'q_af0d482925cc': "RESULT = r0(H.revenue(v, '2026-02-03', '2026-02-03'))\n",
'q_b3db0afa5989': "RESULT = r0(H.group_rev(v, '2025-03-01', '2025-03-31', 'chiên xào'))\n",
'q_ba35baf50768': "RESULT = H.n_orders(v, '2025-11-24', '2025-11-24')\n",
'q_bab1cdc2e19a': "RESULT = r0(H.group_rev(v, '2025-04-01', '2025-04-30', 'lẩu'))\n",
'q_bfacc66b0773': "RESULT = H.days_ge(v, '2025-12-01', '2025-12-31', 44000000)\n",
'q_d29157035ff7': "RESULT = H.n_orders(v, '2026-01-01', '2026-04-06')\n",
'q_daf9cb484194': "RESULT = r0(H.qrev(v, '2026-07-01', '2026-07-31', 'Tôm nướng mọi'))\n",
'q_e22c1a1f335e': "RESULT = H.n_orders(v, '2025-04-01', '2025-06-30')\n",
'q_e81372dda9dc': "RESULT = r0(H.revenue(v, '2026-01-01', '2026-04-27'))\n",
'q_e8216c90595d': "RESULT = r0(H.avg_order(v, '2026-01-05', '2026-01-11'))\n",
'q_e88a5c5df7f1': "RESULT = H.n_orders(v, '2026-01-01', '2026-07-10')\n",
'q_fb027741b529': "RESULT = r0(H.qrev(v, '2025-05-01', '2025-05-31', 'Khô mực nướng'))\n",
}
for q, b in S.items():
    (OUT / f'{q}.py').write_text(PRE + b)
print('wrote', len(S))
