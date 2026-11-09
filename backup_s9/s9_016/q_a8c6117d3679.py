import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_015')
import h117 as H
import pandas as pd

t = H.tables()
ct, gh, nh, ton, bang = t['ct'], t['gh'], t['nh'], t['ton'], t['bang']


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def cust_counts(start, end, minn):
    sub = H.orders_in(ct, start, end)
    per = sub.groupby('Mã phiếu')['TenKH'].first().astype(str).map(H.norm)
    per = per[~per.isin(['khach le', 'le', 'kl', ''])]
    return int((per.value_counts() >= minn).sum())

RESULT = int(round(H.product_qty(ct, '2026-02-01', '2026-02-28', 'Thép Pomina D14 cây 11.7m')))
