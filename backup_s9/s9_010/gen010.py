"""Generate solution files for batch retry9_010."""
from pathlib import Path

OUT = Path('/tmp/s9_010')
OUT.mkdir(exist_ok=True)

PRE112 = '''import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_009')
import h112 as H
import pandas as pd

t = H.tables()
ct = t['ct']
ok = ct['st_norm'] == 'ok'


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def day_range(start, end):
    s = pd.Timestamp(start)
    e = pd.Timestamp(end) + pd.Timedelta(days=1)
    return ok & (ct['dt'] >= s) & (ct['dt'] < e)


def last_week(as_of):
    d = pd.Timestamp(as_of)
    mon = d - pd.Timedelta(days=d.dayofweek)
    return mon - pd.Timedelta(days=7), mon - pd.Timedelta(days=1)


def month_lines(y, m):
    return ct[ok & H.month_mask(ct['dt'], y, m)]


def revenue(mask):
    return float(ct.loc[mask, 'ttien'].sum())


def avg_order(mask):
    rev = revenue(mask)
    n = ct.loc[mask, 'Mã đơn hàng'].nunique()
    return r0(rev / n) if n else 0


def group_rev(y, m, group):
    return r0(H.group_rev(ct, y, m, group))


def qty_product(y, m, name):
    return r0(H.product_qty(ct, y, m, name))


def price_on(name, day):
    d = pd.Timestamp(day)
    sub = ct[(ct['name_n'] == H.norm(name)) & (ct['dt'].dt.normalize() == d)]
    return r0(float(sub['gia'].iloc[0]))
'''

PRE113 = '''import sys
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
'''

S = {}

S['q_8df2a7aa2646'] = ('112', '''
sub = month_lines(2026, 6)
daily = sub.groupby(sub['dt'].dt.normalize())['ttien'].sum()
RESULT = int((daily >= 12_000_000).sum())
''')

S['q_8fad7e1362cd'] = ('112', '''
s, e = last_week('2026-03-21')
RESULT = r0(revenue(ok & (ct['dt'] >= s) & (ct['dt'] <= e)))
''')

S['q_95575307325b'] = ('112', '''
m = ok & (ct['dt'] >= pd.Timestamp('2026-01-01')) & (ct['dt'] <= pd.Timestamp('2026-05-30'))
RESULT = r0(revenue(m))
''')

S['q_97102a98a977'] = ('112', '''
sub = month_lines(2026, 7)
cnt = sub.groupby('name_n')['Mã đơn hàng'].nunique()
RESULT = int((cnt >= 187).sum())
''')

S['q_984d078325ce'] = ('112', '''
RESULT = avg_order(ok & H.month_mask(ct['dt'], 2026, 2))
''')

S['q_9c4f07ffad45'] = ('112', '''
m = ok & (ct['dt'] >= pd.Timestamp('2026-01-01')) & (ct['dt'] <= pd.Timestamp('2026-04-19'))
RESULT = r0(revenue(m))
''')

S['q_9d3c67eadb66'] = ('112', '''
RESULT = group_rev(2025, 7, 'trà sữa')
''')

S['q_9d97b6713f45'] = ('112', '''
RESULT = r0(float(month_lines(2026, 6)['ttien'].sum()))
''')

S['q_a4b8a0ab2b34'] = ('112', '''
RESULT = r0(float(month_lines(2025, 6)['ttien'].sum()))
''')

S['q_ab5bf0b270f3'] = ('112', '''
s, e = last_week('2026-06-25')
sub = ct[ok & (ct['dt'] >= s) & (ct['dt'] <= e) & (ct['Đơn vị tính'] == 'ly')]
RESULT = r0(float(sub['slqd'].sum()))
''')

S['q_b982636a5b87'] = ('112', '''
RESULT = avg_order(ok & H.month_mask(ct['dt'], 2026, 6))
''')

S['q_d54c89f0efc6'] = ('112', '''
RESULT = qty_product(2025, 10, 'Sữa tươi trân châu đường đen (L)')
''')

S['q_d85c9cc71d87'] = ('112', '''
s, e = last_week('2026-01-20')
RESULT = avg_order(ok & (ct['dt'] >= s) & (ct['dt'] <= e))
''')

S['q_da442271d416'] = ('112', '''
sub = month_lines(2026, 6)
daily = sub.groupby(sub['dt'].dt.normalize())['ttien'].sum()
RESULT = int((daily >= 10_000_000).sum())
''')

S['q_dc139d793da1'] = ('112', '''
RESULT = r0(H.size_qty(ct, 2026, 7, 'M'))
''')

S['q_e23c929510f4'] = ('112', '''
RESULT = int(ct.loc[day_range('2025-08-17', '2025-08-23'), 'Mã đơn hàng'].nunique())
''')

S['q_e2cf4535bcaf'] = ('112', '''
s, e = last_week('2025-08-05')
RESULT = avg_order(ok & (ct['dt'] >= s) & (ct['dt'] <= e))
''')

S['q_e509b3da3105'] = ('112', '''
RESULT = group_rev(2026, 6, 'nước ép')
''')

S['q_e9ebd77f74fb'] = ('112', '''
RESULT = price_on('Bạc xỉu (M)', '2025-08-22')
''')

S['q_ec4f8e3b7b41'] = ('112', '''
RESULT = r0(H.size_qty(ct, 2025, 8, 'M'))
''')

S['q_f0565c8a519d'] = ('112', '''
s, e = last_week('2026-05-19')
RESULT = avg_order(ok & (ct['dt'] >= s) & (ct['dt'] <= e))
''')

S['q_1b0010b8da08'] = ('113', '''
key = H.norm('Bộ van dây gas Namilux')
sub = df[month_mask(2025, 12) & (df['name_n'] == key)]
RESULT = int(round(float(sub['qty'].sum())))
''')

S['q_1e534a1eba40'] = ('113', '''
key = H.norm('Dây điện Cadivi VCmd 2x2.5 cuộn 100m')
sub = df[month_mask(2025, 2) & (df['name_n'] == key)]
RESULT = r0(float(sub['rev'].sum()))
''')

S['q_20c6e10447cf'] = ('113', '''
RESULT = r0(float(df.loc[ok & day_mask('2026-06-02'), 'rev'].sum()))
''')

S['q_21ddf8b64394'] = ('113', '''
RESULT = r0(float(df.loc[ok & day_mask('2025-06-26'), 'rev'].sum()))
''')

PRE = {'112': PRE112, '113': PRE113}
for qid, (v, body) in S.items():
    (OUT / f'{qid}.py').write_text(PRE[v] + body)
print('wrote', len(S))
