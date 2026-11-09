import sys
sys.path.insert(0, '/tmp/s9_007')
import h, pandas as pd

u = h.t111()
don, ct, sp, kh, tt = u['don'], u['ct'], u['sp'], u['kh'], u['tt']
ok = don['st_norm'] == 'ok'


def month_mask(dt, y, m):
    return h.month_mask(dt, y, m)


def order_ids(mask):
    return set(don.loc[mask, 'Mã chứng từ'])


def lines_in(mask):
    return ct[ct['Ma don'].isin(order_ids(mask))]


def revenue(mask):
    return float(lines_in(mask)['ttien'].sum())


def qty_of_size(y, m, size):
    sub = lines_in(ok & month_mask(don['dt'], y, m)).merge(sp[['SKU', 'size']], left_on='ID SP', right_on='SKU')
    sub = sub[(sub['size'] == size) & (sub['Đơn vị (tính)'] == 'ly')]
    return int(round(float(sub['slqd'].sum())))


def qty_of_product(y, m, name):
    sku = sp.loc[sp['name_n'] == h.norm(name), 'SKU'].iloc[0]
    sub = lines_in(ok & month_mask(don['dt'], y, m))
    return int(round(float(sub.loc[sub['ID SP'] == sku, 'slqd'].sum())))

d = don[(don['Số KH'].notna()) & (don['Số KH'].astype(str).str.strip() != '')]
d = d[(d['st_norm'] != 'cancel') & (d['conlai'] > 0)]
d = d[d['Phương thức TT'].astype(str).str.strip().str.lower() != 'cod']
RESULT = int(d['Số KH'].nunique())
