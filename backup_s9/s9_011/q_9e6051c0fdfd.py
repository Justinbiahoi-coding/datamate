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
    return ok & (df['dt'] >= d) & (df['dt'] < d + pd.Timedelta(days=1))


def month_mask(y, m):
    s = pd.Timestamp(year=y, month=m, day=1)
    e = s + pd.offsets.MonthBegin(1)
    return ok & (df['dt'] >= s) & (df['dt'] < e)


def revenue(mask):
    return r0(float(df.loc[mask, 'rev'].sum()))


def qty_of(name, mask):
    key = H.norm(name)
    return int(round(float(df.loc[mask & (df['name_n'] == key), 'qty'].sum())))

RESULT = revenue(day_mask(pd.Timestamp('2026-01-29')))
