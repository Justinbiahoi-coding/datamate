import sys
sys.path.insert(0, '/tmp/s9_007')
import h, pandas as pd

t = h.t110()
hd = t['hd']
ok = hd['st_norm'] == 'ok'


def day_mask(day):
    d = pd.Timestamp(day)
    return (hd['dt'] >= d) & (hd['dt'] < d + pd.Timedelta(days=1))


def month_mask(y, m):
    s = pd.Timestamp(year=y, month=m, day=1)
    e = s + pd.offsets.MonthBegin(1)
    return ok & (hd['dt'] >= s) & (hd['dt'] < e)

RESULT = int(round(float(hd.loc[month_mask(2026, 4), 'rev'].sum())))
