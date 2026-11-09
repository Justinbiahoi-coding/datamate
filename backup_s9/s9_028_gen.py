from pathlib import Path
OUT = Path('/tmp/s9_028'); OUT.mkdir(exist_ok=True)
PRE = '''import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_027')
import h129 as H
import pandas as pd

t = H.tables()
dh, ct, tt, sp = t['dh'], t['ct'], t['tt'], t['sp']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def rank_rev(rank, a, b):
    s, e = pd.Timestamp(a), pd.Timestamp(b) + pd.Timedelta(days=1)
    ids = set(dh[dh['valid'] & (dh['dt'] >= s) & (dh['dt'] < e)
                 & (dh['cust_rank'] == H.norm(rank))]['Số phiếu'])
    return float(ct[ct['Số CT'].isin(ids)]['rev'].sum())


def debt_at(asof):
    a = pd.Timestamp(asof) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    d = dh[(~dh['cancelled']) & (dh['dt'] <= a) & (dh['Hình thức thanh toán'] != 'cod')].copy()
    paid = tt[tt['dt'] <= a].groupby('Mã giao dịch')['amount'].sum()
    d['paid_calc'] = d['Số phiếu'].map(paid).fillna(0)
    d['out'] = d['total'] - d['paid_calc']
    return d[d['out'] > 0]
'''
S = {
'q_9cbdf3a6ec79': "RESULT = r0(H.collections(dh, tt, '2026-08-01', '2026-08-14'))\n",
'q_9de78b7e6230': "RESULT = r0(H.avg_order(ct, dh, '2026-06-01', '2026-06-30'))\n",
'q_a076d04e713e': "RESULT = r0(H.collections(dh, tt, '2025-10-01', '2025-10-31'))\n",
'q_aac53183ff41': "RESULT = H.cancelled_count(dh, '2026-02-01', '2026-02-28')\n",
'q_ac40afedce04': "RESULT = r0(H.avg_order(ct, dh, '2025-07-01', '2025-07-31'))\n",
'q_b602a57b38a4': "RESULT = f\"{H.group_rev(ct, dh, '2025-07-01', '2025-07-31', 'chiên xào') / H.revenue(ct, dh, '2025-07-01', '2025-07-31') * 100:.2f}%\"\n",
'q_bdfa11fe0170': "RESULT = r0(H.qrev(ct, dh, '2025-04-01', '2025-04-30', 'Giò heo muối chiên giòn'))\n",
'q_ce98842bb9b6': "RESULT = r0(H.qty(ct, dh, '2025-01-01', '2025-01-31', 'Đậu que xào tỏi'))\n",
'q_ce9d69872fae': "RESULT = r0(H.qrev(ct, dh, '2026-03-01', '2026-03-31', 'Má heo nướng nước mắm'))\n",
'q_d2e70de5d8c1': "RESULT = r0(H.revenue(ct, dh, '2025-11-01', '2025-11-30'))\n",
'q_d361c00c6829': "RESULT = r0(rank_rev('thân thiết', '2025-06-01', '2025-06-30'))\n",
'q_d42f7061820b': "RESULT = H.cancelled_count(dh, '2026-05-01', '2026-05-31')\n",
'q_d83d7d5fc1e1': "RESULT = r0(H.revenue(ct, dh, '2026-01-01', '2026-01-31'))\n",
'q_df8676bd0c48': "RESULT = r0(H.qrev(ct, dh, '2025-03-01', '2025-03-31', 'Giò heo muối chiên giòn'))\n",
'q_e1749edb84bb': "RESULT = r0(H.avg_order(ct, dh, '2026-07-01', '2026-07-31'))\n",
'q_e9aff6f7b58e': "RESULT = r0(H.revenue(ct, dh, '2025-05-22', '2025-05-22'))\n",
'q_ea88d1f6dcfd': "RESULT = r0(H.revenue(ct, dh, '2025-09-01', '2025-09-30'))\n",
'q_ebfba62ad2d4': "RESULT = H.n_orders(dh, '2025-07-01', '2025-09-30')\n",
'q_ecf144db70a1': "RESULT = r0(debt_at('2026-08-14')['out'].sum())\n",
'q_f0123548f973': "RESULT = r0(H.qty(ct, dh, '2025-05-01', '2025-05-31', 'Gỏi ngó sen tôm thịt'))\n",
'q_f6a1f1419974': "RESULT = r0(H.price_on_day(ct, 'Nghêu hấp sả', '2025-11-16'))\n",
'q_fe67932c2f2e': "RESULT = r0(H.avg_order(ct, dh, '2025-03-01', '2025-03-31'))\n",
}
for q, b in S.items():
    (OUT / f'{q}.py').write_text(PRE + b)
print('wrote', len(S))
