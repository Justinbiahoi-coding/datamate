import sys
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
RESULT = f"{H.group_rev(ct, dh, '2025-07-01', '2025-07-31', 'chiên xào') / H.revenue(ct, dh, '2025-07-01', '2025-07-31') * 100:.2f}%"
