"""Generate solution files for batch retry9_012."""
from pathlib import Path

OUT = Path('/tmp/s9_012')
OUT.mkdir(exist_ok=True)

PRE114 = '''import sys, re
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
    m = re.search(r'\\d+', str(s))
    return float(m.group()) if m else 1.0


def unit_price(day, name):
    """Unit price for ONE base unit on a given day."""
    d = pd.Timestamp(day)
    sub = df[(df['dt'].dt.normalize() == d) & (df['name_n'] == H.norm(name))]
    row = sub.iloc[0]
    factor = float(row['qty']) / sl_numeric(row['Sluong'])
    return r0(float(H.money(row['Giá bán lẻ'])) / (factor if factor else 1.0))
'''

PRE115 = '''import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_012')
import h115 as H
import pandas as pd

t = H.tables()
ct, sp = t['ct'], t['sp']
ok = ct['st_norm'] == 'ok'


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def day_mask(day):
    d = pd.Timestamp(day)
    return ok & (ct['dt'] >= d) & (ct['dt'] < d + pd.Timedelta(days=1))


def month_mask(y, m):
    return ok & H.month_mask(ct['dt'], y, m)


def revenue(mask):
    return r0(float(ct.loc[mask, 'ttien'].sum()))


def avg_order(mask):
    rev = float(ct.loc[mask, 'ttien'].sum())
    n = ct.loc[mask, 'Mã đơn hàng'].nunique()
    return r0(rev / n) if n else 0


def orders(mask):
    return int(ct.loc[mask, 'Mã đơn hàng'].nunique())
'''

S = {}

# ── biz_114 ────────────────────────────────────────────────────────────────
S['q_d169d950bfd8'] = ('114', '''
RESULT = revenue(month_mask(2025, 3))
''')

S['q_d5e6651d3fb6'] = ('114', '''
RESULT = unit_price('2025-07-02', 'Gạch thẻ đặc 4x8x18')
''')

S['q_dcf142759a5a'] = ('114', '''
RESULT = revenue(day_mask(pd.Timestamp('2025-07-15') - pd.Timedelta(days=1)))
''')

S['q_e70c76062701'] = ('114', '''
RESULT = revenue(month_mask(2026, 3))
''')

S['q_edac1af0eaa6'] = ('114', '''
RESULT = unit_price('2026-01-01', 'Bộ van dây gas Namilux')
''')

# ── biz_115 ────────────────────────────────────────────────────────────────
S['q_05aca83bd353'] = ('115', '''
RESULT = H.stale_items(ct, '2025-10-20', '2025-10-26')
''')

S['q_15f526794b65'] = ('115', '''
m = (ct['st_norm'] == 'cancel') & H.month_mask(ct['dt'], 2025, 10)
RESULT = orders(m)
''')

S['q_1c7f07d0f4bc'] = ('115', '''
RESULT = r0(H.group_rev(ct, 2025, 9, 'gas & nước'))
''')

S['q_1cf0e17b3e1b'] = ('115', '''
RESULT = revenue(month_mask(2026, 4))
''')

S['q_229136869fd0'] = ('115', '''
RESULT = revenue(day_mask(pd.Timestamp('2026-01-24') - pd.Timedelta(days=1)))
''')

S['q_2b77f6e637a2'] = ('115', '''
RESULT = r0(H.product_rev(ct, 2025, 7, 'Nước khoáng Lavie 19L'))
''')

S['q_36003fd74fae'] = ('115', '''
RESULT = r0(H.group_rev(ct, 2025, 3, 'cát đá'))
''')

S['q_39862a30b7df'] = ('115', '''
m = ok & (ct['dt'] >= pd.Timestamp('2025-04-01')) & (ct['dt'] < pd.Timestamp('2025-07-01'))
RESULT = orders(m)
''')

S['q_3bacbb6247bb'] = ('115', '''
RESULT = avg_order(month_mask(2025, 11))
''')

S['q_451992e04c6f'] = ('115', '''
RESULT = H.stale_items(ct, '2025-05-06', '2025-05-12')
''')

S['q_5bfa9714a91b'] = ('115', '''
RESULT = revenue(day_mask(pd.Timestamp('2026-03-01') - pd.Timedelta(days=1)))
''')

S['q_5d3ed455f3c8'] = ('115', '''
m = ok & (ct['dt'] >= pd.Timestamp('2026-01-01')) & (ct['dt'] < pd.Timestamp('2026-04-01'))
RESULT = orders(m)
''')

S['q_5f4cb9a524ff'] = ('115', '''
RESULT = H.stale_items(ct, '2026-02-20', '2026-02-26')
''')

S['q_6bb45ebc096d'] = ('115', '''
RESULT = int(round(H.product_qty(ct, '2026-04-01', '2026-04-30', 'Thép Pomina D16 cây 11.7m')))
''')

S['q_73e8e916caa4'] = ('115', '''
RESULT = avg_order(month_mask(2026, 2))
''')

S['q_7b87e9384485'] = ('115', '''
RESULT = r0(H.product_rev(ct, 2025, 4, 'Ống PVC Bình Minh D50 cây 4m'))
''')

S['q_815ed7778bf4'] = ('115', '''
RESULT = orders(day_mask(pd.Timestamp('2026-02-01') - pd.Timedelta(days=1)))
''')

S['q_82ab0dd948e0'] = ('115', '''
RESULT = avg_order(month_mask(2025, 12))
''')

S['q_87fa97c6ea8c'] = ('115', '''
RESULT = r0(H.product_rev(ct, 2025, 12, 'Nước tinh khiết Vihawa 20L'))
''')

S['q_8b533d790ead'] = ('115', '''
RESULT = int(round(H.product_qty(ct, '2025-05-01', '2025-05-31', 'Thước thủy nhôm Total 60cm')))
''')

PRE = {'114': PRE114, '115': PRE115}

for qid, (v, body) in S.items():
    (OUT / f'{qid}.py').write_text(PRE[v] + body)
print('wrote', len(S))
