import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_022')
import h124 as H
import pandas as pd

t = H.tables()
hd, ct, hh, nh, tk, pt, kh = t['hd'], t['ct'], t['hh'], t['nh'], t['tk'], t['pt'], t['kh']

import sys as _s
_s.path.insert(0, '/Users/buivanthien/Learn/zalo chelen/datamate/code')
from pathlib import Path as _P
from loader import load_business as _lb
_b = _lb(_P('/Users/buivanthien/Learn/zalo chelen/datamate/train/data/biz_124'))


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def chiphi():
    cp = _b['SoTay_ChiPhi'].copy()
    cp['dt'] = cp['Ngày chi'].map(H.to_date)
    cp['amt'] = cp['So tien'].map(H.money)
    return cp


def net_profit(y, m):
    s = pd.Timestamp(y, m, 1)
    e = s + pd.offsets.MonthBegin(1)
    ids = set(hd[hd['valid'] & (hd['dt'] >= s) & (hd['dt'] < e)]['Order ID'])
    sub = ct[ct['Mã giao dịch'].isin(ids)]
    rev = sub['rev'].sum()
    cost = (sub['cost'] * sub['slg']).sum()
    exp = chiphi()
    exp = exp[(exp['dt'] >= s) & (exp['dt'] < e)]['amt'].sum()
    return rev - cost - exp

row = tk[tk['Hàng hóa'].map(H.norm) == H.norm('Plusssz Max Multivitamin viên sủi tuýp 20 viên')]
RESULT = r0(float(row['stock'].sum()))
