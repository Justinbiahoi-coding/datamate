import sys
sys.path.insert(0, '/tmp/s9_007')
import h, pandas as pd

t = h.t109()
hd, ct, sp = t['hd'], t['ct'], t['sp']
ok = hd['st_norm'] == 'ok'


def month_mask(y, m):
    s = pd.Timestamp(year=y, month=m, day=1)
    e = s + pd.offsets.MonthBegin(1)
    return ok & (hd['dt'] >= s) & (hd['dt'] < e)


def lines_in(mask):
    return ct[ct['Mã hóa đơn'].isin(set(hd.loc[mask, 'Mã hóa đơn']))]

sub = lines_in(month_mask(2025, 8))
RESULT = int(round(float(sub['Thành tiền_n'].sum())))
