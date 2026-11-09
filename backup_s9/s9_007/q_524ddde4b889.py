import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/tmp/s9_007')
import h, pandas as pd

u = h.t111()
don, ct, sp, kh, tt = u['don'], u['ct'], u['sp'], u['kh'], u['tt']
ok = don['st_norm'] == 'ok'


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def r2(x):
    return Decimal(str(float(x))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def ids_of(mask):
    return set(don.loc[mask, 'Mã chứng từ'])


def lines_in(mask):
    return ct[ct['Ma don'].isin(ids_of(mask))]


def revenue(mask):
    return float(lines_in(mask)['ttien'].sum())


def day_mask(day):
    d = pd.Timestamp(day)
    return (don['dt'] >= d) & (don['dt'] < d + pd.Timedelta(days=1))


def qty_of_size(y, m, size):
    sub = lines_in(ok & h.month_mask(don['dt'], y, m)).merge(
        sp[['SKU', 'size']], left_on='ID SP', right_on='SKU')
    sub = sub[(sub['size'] == size) & (sub['Đơn vị (tính)'] == 'ly')]
    return r0(float(sub['slqd'].sum()))


def qty_of_product(y, m, name):
    sku = sp.loc[sp['name_n'] == h.norm(name), 'SKU'].iloc[0]
    sub = lines_in(ok & h.month_mask(don['dt'], y, m))
    return r0(float(sub.loc[sub['ID SP'] == sku, 'slqd'].sum()))


def repayments(start, end):
    credit = don[(don['Phương thức TT'].astype(str).str.strip() == 'debt') &
                 (don['st_norm'] != 'cancel')][['Mã chứng từ', 'dt']]
    q = tt.merge(credit, left_on='Số HĐ', right_on='Mã chứng từ')
    q = q[(q['dt_x'] >= pd.Timestamp(start)) & (q['dt_x'] < pd.Timestamp(end))]
    q = q[q['dt_x'].dt.normalize() > q['dt_y'].dt.normalize()]
    return r0(float(q['tien'].sum()))

RESULT = r0(revenue(ok & h.month_mask(don['dt'], 2025, 1)))
