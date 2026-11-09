import sys, re
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_011')
import h114 as H
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


def sl_numeric(s):
    m = re.search(r'\d+', str(s))
    return float(m.group()) if m else 1.0


def unit_price(day, name):
    """Unit price for ONE base unit on a given day."""
    d = pd.Timestamp(day)
    sub = df[(df['dt'].dt.normalize() == d) & (df['name_n'] == H.norm(name))]
    row = sub.iloc[0]
    factor = float(row['qty']) / sl_numeric(row['Sluong'])
    return r0(float(H.money(row['Giá bán lẻ'])) / (factor if factor else 1.0))

RESULT = revenue(month_mask(2026, 3))
