from pathlib import Path
OUT = Path('/tmp/s9_027'); OUT.mkdir(exist_ok=True)
PRE = '''import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_027')
import h129 as H
import pandas as pd

t = H.tables()
dh, ct, tt, sp = t['dh'], t['ct'], t['tt'], t['sp']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
'''
S = {
'q_0eebfe5b43c4': "RESULT = r0(H.revenue(ct, dh, '2025-01-01', '2025-03-31'))\n",
'q_113fb704f84d': "RESULT = H.n_orders(dh, '2025-04-24', '2025-04-24')\n",
'q_1915a6fd7b94': "RESULT = r0(H.price_on_day(ct, 'Rau củ kho quẹt', '2025-11-14'))\n",
'q_1ef86d51bc58': "RESULT = H.cancelled_count(dh, '2025-08-01', '2025-08-31')\n",
'q_22066f683e43': "RESULT = r0(H.avg_order(ct, dh, '2025-05-01', '2025-05-31'))\n",
'q_2415771378b9': "RESULT = r0(H.revenue(ct, dh, '2025-12-01', '2025-12-31'))\n",
'q_3094bfe79729': "RESULT = H.n_orders(dh, '2026-01-06', '2026-01-06')\n",
'q_3391a2ab7a86': "RESULT = r0(H.cash_rev(ct, dh, '2026-08-01', '2026-08-14'))\n",
'q_38030489a1b6': "RESULT = r0(H.avg_order(ct, dh, '2026-04-01', '2026-04-30'))\n",
'q_3e7f21910845': "RESULT = H.cancelled_count(dh, '2025-06-01', '2025-06-30')\n",
'q_4bbd72655e8e': "RESULT = r0(H.qty(ct, dh, '2025-09-01', '2025-09-30', 'Chân gà ngâm sả tắc'))\n",
'q_4dc24191967d': "RESULT = r0(H.revenue(ct, dh, '2026-04-28', '2026-04-28'))\n",
'q_572b12b7c64a': "RESULT = r0(H.qrev(ct, dh, '2025-01-01', '2025-01-31', 'Chân gà nướng'))\n",
'q_5b2645b8ddc7': "RESULT = r0(H.price_on_day(ct, 'Ốc bươu nhồi thịt', '2025-10-21'))\n",
'q_61668efd96c5': "RESULT = r0(H.revenue(ct, dh, '2025-11-02', '2025-11-02'))\n",
'q_71f5dee2b82b': "RESULT = r0(H.qrev(ct, dh, '2025-08-01', '2025-08-31', 'Gỏi khoai môn hải sản'))\n",
'q_72f8db64e438': "RESULT = r0(H.avg_order(ct, dh, '2025-06-01', '2025-06-30'))\n",
'q_73d64040f361': "RESULT = H.cancelled_count(dh, '2025-10-01', '2025-10-31')\n",
'q_7766254adf84': "RESULT = r0(H.collections(dh, tt, '2025-09-01', '2025-09-30'))\n",
'q_7a0a2623efab': "RESULT = H.n_orders(dh, '2025-12-24', '2025-12-24')\n",
'q_82581d0c17e0': "RESULT = f\"{H.group_rev(ct, dh, '2025-10-01', '2025-10-31', 'cơm mì cháo') / H.revenue(ct, dh, '2025-10-01', '2025-10-31') * 100:.2f}%\"\n",
'q_88a224ef1656': "RESULT = H.n_orders(dh, '2025-02-20', '2025-02-20')\n",
'q_8baf445f3784': "RESULT = r0(H.revenue(ct, dh, '2025-06-01', '2025-06-30'))\n",
'q_92d3d19aeafa': "RESULT = r0(H.revenue(ct, dh, '2026-05-31', '2026-05-31'))\n",
'q_9c1c163ad795': "RESULT = r0(H.revenue(ct, dh, '2025-04-01', '2025-04-30'))\n",
}
for q, b in S.items():
    (OUT / f'{q}.py').write_text(PRE + b)
print('wrote', len(S))
