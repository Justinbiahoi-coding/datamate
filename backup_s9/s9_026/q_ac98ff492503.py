import sys
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
RESULT = r0(H.qrev(ct, dh, '2026-04-01', '2026-04-30', 'Chanh đá'))
