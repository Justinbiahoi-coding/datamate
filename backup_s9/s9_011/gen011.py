"""Generate solution files for batch retry9_011."""
from pathlib import Path

OUT = Path('/tmp/s9_011')
OUT.mkdir(exist_ok=True)

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
'''

PRE114 = '''import sys
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


def qty_of(name, mask):
    key = H.norm(name)
    return int(round(float(df.loc[mask & (df['name_n'] == key), 'qty'].sum())))
'''

S = {}

# ── biz_113 ────────────────────────────────────────────────────────────────
S['q_4100ffcaa83c'] = ('113', '''
RESULT = revenue(month_mask(2026, 5))
''')

S['q_6595892c9fd3'] = ('113', '''
RESULT = qty_of('Bộ van dây gas Namilux', month_mask(2025, 8))
''')

S['q_6be56589f795'] = ('113', '''
RESULT = revenue(day_mask(pd.Timestamp('2026-02-06') - pd.Timedelta(days=1)))
''')

S['q_756cb06c26cc'] = ('113', '''
RESULT = revenue(month_mask(2026, 2) & (df['name_n'] == H.norm('Công tắc 1 chiều Panasonic Wide kèm mặt')))
''')

S['q_7bc480d14863'] = ('113', '''
RESULT = revenue(day_mask(pd.Timestamp('2025-04-10') - pd.Timedelta(days=1)))
''')

S['q_7bc4d0438365'] = ('113', '''
RESULT = revenue(day_mask(pd.Timestamp('2025-09-24') - pd.Timedelta(days=1)))
''')

S['q_845aac1e65f8'] = ('113', '''
RESULT = revenue(day_mask(pd.Timestamp('2025-10-25') - pd.Timedelta(days=1)))
''')

S['q_96b02e2deb36'] = ('113', '''
RESULT = revenue(day_mask(pd.Timestamp('2026-06-23') - pd.Timedelta(days=1)))
''')

S['q_9e6051c0fdfd'] = ('113', '''
RESULT = revenue(day_mask(pd.Timestamp('2026-01-29')))
''')

S['q_adcc2d9582ae'] = ('113', '''
RESULT = revenue(ok & (df['dt'] >= pd.Timestamp('2026-04-01')) & (df['dt'] < pd.Timestamp('2026-07-01')))
''')

S['q_c6db2e5f95d6'] = ('113', '''
RESULT = revenue(day_mask(pd.Timestamp('2026-02-20') - pd.Timedelta(days=1)))
''')

S['q_db2e7a620398'] = ('113', '''
RESULT = qty_of('Thép cuộn phi 8 Hòa Phát', month_mask(2026, 1))
''')

S['q_dce63804b1d8'] = ('113', '''
RESULT = qty_of('Gạch lát nền Prime 60x60 thùng 4 viên', month_mask(2026, 5))
''')

S['q_ebdf2a0cd67e'] = ('113', '''
RESULT = revenue(day_mask(pd.Timestamp('2025-09-02')))
''')

S['q_f0c071b28ce8'] = ('113', '''
RESULT = revenue(month_mask(2025, 4))
''')

S['q_f0f76f4dbcb7'] = ('113', '''
RESULT = qty_of('Ống PVC Bình Minh D50 cây 4m', month_mask(2025, 12))
''')

S['q_f490b558605d'] = ('113', '''
RESULT = qty_of('Thép cuộn phi 8 Hòa Phát', month_mask(2025, 5))
''')

# ── biz_114 ────────────────────────────────────────────────────────────────
S['q_15fc10ffaea0'] = ('114', '''
RESULT = revenue(day_mask(pd.Timestamp('2026-03-22') - pd.Timedelta(days=1)))
''')

S['q_2e6c7ad83383'] = ('114', '''
RESULT = qty_of('Keo dán ống PVC Bình Minh 200g', month_mask(2025, 2))
''')

S['q_62e395a64ba0'] = ('114', '''
RESULT = revenue(ok & (df['dt'] >= pd.Timestamp('2025-07-01')) & (df['dt'] < pd.Timestamp('2025-10-01')))
''')

S['q_689b129e020c'] = ('114', '''
RESULT = qty_of('Sơn lót Jotun Jotashield chống kiềm 5L', month_mask(2026, 2))
''')

S['q_7d6fb7dc61e6'] = ('114', '''
RESULT = revenue(month_mask(2025, 11))
''')

S['q_81d119a55e5c'] = ('114', '''
RESULT = int(df.loc[day_mask(pd.Timestamp('2025-07-25')), 'Mã GD'].nunique())
''')

S['q_9a9d18b10b6e'] = ('114', '''
RESULT = int(df.loc[day_mask(pd.Timestamp('2025-04-06') - pd.Timedelta(days=1)), 'Mã GD'].nunique())
''')

S['q_b5c41bf00e07'] = ('114', '''
RESULT = revenue(day_mask(pd.Timestamp('2025-05-07') - pd.Timedelta(days=1)))
''')

PRE = {'113': PRE113, '114': PRE114}

for qid, (v, body) in S.items():
    (OUT / f'{qid}.py').write_text(PRE[v] + body)
print('wrote', len(S))
