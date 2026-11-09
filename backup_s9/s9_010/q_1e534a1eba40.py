import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_010')
import h113 as H
import pandas as pd

df = H.tables()
ok = df['st_norm'] == 'ok'


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def day_mask(day):
    d = pd.Timestamp(day)
    return (df['dt'] >= d) & (df['dt'] < d + pd.Timedelta(days=1))


def month_mask(y, m):
    s = pd.Timestamp(year=y, month=m, day=1)
    e = s + pd.offsets.MonthBegin(1)
    return ok & (df['dt'] >= s) & (df['dt'] < e)

key = H.norm('Dây điện Cadivi VCmd 2x2.5 cuộn 100m')
sub = df[month_mask(2025, 2) & (df['name_n'] == key)]
RESULT = r0(float(sub['rev'].sum()))
