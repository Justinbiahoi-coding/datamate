"""Generate solution files for batch retry9_009."""
from pathlib import Path

OUT = Path('/tmp/s9_009')
OUT.mkdir(exist_ok=True)

PRE112 = '''import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_009')
import h112 as H
import pandas as pd

t = H.tables()
ct, sp = t['ct'], t['sp']
ok = ct['st_norm'] == 'ok'


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def day_range(start, end):
    s = pd.Timestamp(start)
    e = pd.Timestamp(end) + pd.Timedelta(days=1)
    return ok & (ct['dt'] >= s) & (ct['dt'] < e)


def month_lines(y, m):
    return ct[ok & H.month_mask(ct['dt'], y, m)]


def revenue(mask):
    return float(ct.loc[mask, 'ttien'].sum())


def order_revenue(y, m=None):
    sub = ct[ok & (H.month_mask(ct['dt'], y, m) if m else pd.Series(True, index=ct.index))]
    return sub.groupby('Mã đơn hàng')['ttien'].sum()


def last_week(as_of):
    d = pd.Timestamp(as_of)
    mon = d - pd.Timedelta(days=d.dayofweek)
    return mon - pd.Timedelta(days=7), mon - pd.Timedelta(days=1)


def qty_size(y, m, size):
    return r0(H.size_qty(ct, y, m, size))


def qty_product(y, m, name):
    return r0(H.product_qty(ct, y, m, name))


def group_rev(y, m, group):
    return r0(H.group_rev(ct, y, m, group))


def prod_rev(y, m, name):
    return r0(H.product_rev(ct, y, m, name))
'''

PRE111 = '''import sys
sys.path.insert(0, '/tmp/s9_007')
import h
import pandas as pd

u = h.t111()
don, tt = u['don'], u['tt']


def repayments(start, end):
    credit = don[(don['Phương thức TT'].astype(str).str.strip() == 'debt') &
                 (don['st_norm'] != 'cancel')][['Mã chứng từ', 'dt']]
    q = tt.merge(credit, left_on='Số HĐ', right_on='Mã chứng từ')
    q = q[(q['dt_x'] >= pd.Timestamp(start)) & (q['dt_x'] < pd.Timestamp(end))]
    q = q[q['dt_x'].dt.normalize() > q['dt_y'].dt.normalize()]
    return int(round(float(q['tien'].sum())))
'''

S = {}

S['q_f0859c5b2adb'] = ('111', '''
RESULT = repayments('2025-08-01', '2025-09-01')
''')

S['q_01a28f2233bd'] = ('112', '''
day = pd.Timestamp('2025-12-01')
sub = ct[(ct['name_n'] == H.norm('Soda chanh dây (M)')) & (ct['dt'].dt.normalize() == day)]
RESULT = r0(float(sub['gia'].iloc[0]))
''')

S['q_04f73179d0fe'] = ('112', '''
RESULT = group_rev(2025, 10, 'trà sữa')
''')

S['q_181453dd6752'] = ('112', '''
sub = ct[ok & (ct['dt'] >= pd.Timestamp('2026-01-01')) & (ct['dt'] <= pd.Timestamp('2026-02-22'))]
RESULT = int(sub['Mã đơn hàng'].nunique())
''')

S['q_25a74f03c947'] = ('112', '''
s, e = last_week('2025-07-15')
m = ok & (ct['dt'] >= s) & (ct['dt'] <= e)
rev = revenue(m)
n = ct.loc[m, 'Mã đơn hàng'].nunique()
RESULT = r0(rev / n) if n else 0
''')

S['q_277c700a360c'] = ('112', '''
m = ok & (ct['dt'] >= pd.Timestamp('2026-01-01')) & (ct['dt'] <= pd.Timestamp('2026-03-06'))
RESULT = r0(revenue(m))
''')

S['q_40fde817403c'] = ('112', '''
m = day_range('2026-07-20', '2026-07-26')
RESULT = int(ct.loc[m, 'Mã đơn hàng'].nunique())
''')

S['q_41c306df830d'] = ('112', '''
sub = month_lines(2025, 6)
per_order = sub.groupby('Mã đơn hàng')['ttien'].sum()
RESULT = int((per_order >= 93000).sum())
''')

S['q_48fe8e662427'] = ('112', '''
d = pd.Timestamp('2025-07-05')
mon = d - pd.Timedelta(days=d.dayofweek)
m = ok & (ct['dt'] >= mon) & (ct['dt'] <= d)
RESULT = r0(revenue(m))
''')

S['q_4ccbb48dfae2'] = ('112', '''
RESULT = qty_size(2025, 4, 'M')
''')

S['q_4f9117864544'] = ('112', '''
m = ok & (ct['dt'] >= pd.Timestamp('2026-01-01')) & (ct['dt'] <= pd.Timestamp('2026-04-30'))
RESULT = r0(revenue(m))
''')

S['q_53a9f8d7a09b'] = ('112', '''
RESULT = group_rev(2026, 6, 'đá xay')
''')

S['q_5fe73625357e'] = ('112', '''
RESULT = prod_rev(2025, 12, 'Soda chanh dây (M)')
''')

S['q_65910a3f8224'] = ('112', '''
RESULT = r0(float(month_lines(2026, 1)['ttien'].sum()))
''')

S['q_65c45c449b96'] = ('112', '''
RESULT = qty_size(2025, 8, 'L')
''')

S['q_6c2af3b5e004'] = ('112', '''
RESULT = prod_rev(2026, 1, 'Espresso (double)')
''')

S['q_70e2095d86ac'] = ('112', '''
d = pd.Timestamp('2025-11-05')
m = ok & (ct['dt'] > d - pd.Timedelta(days=30)) & (ct['dt'] <= d)
RESULT = r0(revenue(m))
''')

S['q_766c79feaf8e'] = ('112', '''
s, e = last_week('2026-03-24')
m = ok & (ct['dt'] >= s) & (ct['dt'] <= e)
rev = revenue(m)
n = ct.loc[m, 'Mã đơn hàng'].nunique()
RESULT = r0(rev / n) if n else 0
''')

S['q_77b5d0d4b2df'] = ('112', '''
RESULT = r0(revenue(day_range('2026-04-16', '2026-04-22')))
''')

S['q_7b4a5ac53f30'] = ('112', '''
RESULT = r0(float(month_lines(2025, 5)['ttien'].sum()))
''')

S['q_7c0a4b5f5196'] = ('112', '''
sub = month_lines(2026, 5)
daily = sub.groupby(sub['dt'].dt.normalize())['ttien'].sum()
RESULT = int((daily >= 11_000_000).sum())
''')

S['q_85b6e200e248'] = ('112', '''
RESULT = qty_size(2025, 10, 'L')
''')

S['q_879eefef8caa'] = ('112', '''
s, e = last_week('2026-03-16')
RESULT = r0(revenue(ok & (ct['dt'] >= s) & (ct['dt'] <= e)))
''')

S['q_8b18ac4853bf'] = ('112', '''
RESULT = group_rev(2026, 5, 'nước ép')
''')

S['q_8dc767d33cd7'] = ('112', '''
s, e = last_week('2025-07-29')
m = ok & (ct['dt'] >= s) & (ct['dt'] <= e)
rev = revenue(m)
n = ct.loc[m, 'Mã đơn hàng'].nunique()
RESULT = r0(rev / n) if n else 0
''')

PRE = {'112': PRE112, '111': PRE111}

for qid, (v, body) in S.items():
    (OUT / f'{qid}.py').write_text(PRE[v] + body)
print('wrote', len(S))
