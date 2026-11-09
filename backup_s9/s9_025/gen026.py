from pathlib import Path
OUT = Path('/tmp/s9_026'); OUT.mkdir(exist_ok=True)
PRE = '''import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_025')
import h127 as H
import pandas as pd

t = H.tables()
dh, ct, tt, sp = t['dh'], t['ct'], t['tt'], t['sp']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def grev(g, a, b):
    ids = set(H.orders_in(dh, a, b)['Mã chứng từ'])
    s = ct[ct['Mã đơn hàng'].isin(ids) & (ct['group_n'] == H.norm(g))]
    return float(s['rev'].sum())


def unit_qty(unit, a, b):
    ids = set(H.orders_in(dh, a, b)['Mã chứng từ'])
    s = ct[ct['Mã đơn hàng'].isin(ids) & (ct['base_unit'] == unit)]
    return float(s['qty'].sum())
'''
S = {
'q_4dc0ead903ab': "RESULT = r0(grev('gỏi', '2025-04-01', '2025-04-30'))\n",
'q_507a4f0e1ee9': "RESULT = r0(H.revenue(ct, dh, '2025-04-29', '2025-04-29'))\n",
'q_5a1e29a88b63': "RESULT = r0(H.revenue(ct, dh, '2026-04-03', '2026-04-03'))\n",
'q_5b5eca8b20c3': "RESULT = r0(H.qrev(ct, dh, '2025-08-01', '2025-08-31', 'Lẩu gà lá é'))\n",
'q_5f19f856c63f': "RESULT = r0(H.revenue(ct, dh, '2025-11-01', '2025-11-30'))\n",
'q_5f83d53153e5': "RESULT = r0(H.qty(ct, dh, '2025-04-01', '2025-04-30', 'Rau củ kho quẹt'))\n",
'q_624df3df3254': "RESULT = r0(H.revenue(ct, dh, '2025-07-04', '2025-07-04'))\n",
'q_6cb66fd47ab6': "RESULT = r0(unit_qty('lon', '2025-12-27', '2025-12-27'))\n",
'q_6df1acd987f0': "RESULT = r0(unit_qty('nồi', '2025-12-01', '2025-12-01'))\n",
'q_7404fd9ff636': "RESULT = H.n_orders(dh, '2026-03-31', '2026-03-31')\n",
'q_891f3936588a': "RESULT = r0(H.qty(ct, dh, '2025-04-01', '2025-04-30', 'Sụn gà rang muối'))\n",
'q_992dd83fe5d0': "RESULT = r0(H.revenue(ct, dh, '2025-10-19', '2025-10-19'))\n",
'q_a216b24ccdfd': "RESULT = H.n_orders(dh, '2025-09-02', '2025-09-02')\n",
'q_a51671b6bc3c': "RESULT = H.cancelled_count(dh, '2026-03-01', '2026-03-31')\n",
'q_a547a1f6ac6f': "RESULT = r0(H.revenue(ct, dh, '2025-10-01', '2025-12-31'))\n",
'q_a82b7d1477f8': "RESULT = r0(H.revenue(ct, dh, '2026-02-01', '2026-02-28'))\n",
'q_ac98ff492503': "RESULT = r0(H.qrev(ct, dh, '2026-04-01', '2026-04-30', 'Chanh đá'))\n",
'q_b51094c20fd5': "RESULT = r0(H.revenue(ct, dh, '2025-07-18', '2025-07-18'))\n",
'q_b7ba1a62cf38': "RESULT = r0(H.qty(ct, dh, '2025-03-01', '2025-03-31', 'Canh chua cá lóc'))\n",
'q_d96319549a49': "RESULT = r0(H.avg_order(ct, dh, '2025-07-01', '2025-07-31'))\n",
'q_e0feae509b24': "RESULT = r0(H.collections(dh, tt, '2025-06-01', '2025-06-30'))\n",
'q_ecad7ca9cd8b': "RESULT = r0(H.avg_order(ct, dh, '2025-05-01', '2025-05-31'))\n",
'q_f01a6c708329': "RESULT = r0(H.revenue(ct, dh, '2026-01-01', '2026-01-31'))\n",
'q_f4cba6071b48': "RESULT = r0(H.avg_order(ct, dh, '2025-09-01', '2025-09-30'))\n",
'q_fa7a082fc6b6': "RESULT = r0(H.revenue(ct, dh, '2025-07-22', '2025-07-22'))\n",
}
for q, b in S.items():
    (OUT / f'{q}.py').write_text(PRE + b)
print('wrote', len(S))
