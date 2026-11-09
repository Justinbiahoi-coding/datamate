import sys
sys.path.insert(0, '/tmp/s9_006')
import h, pandas as pd

t = h.tables()
hd, ct = t['hd'], t['ct']
ok = hd['st_norm'] == 'ok'


def rev(mask):
    ids = set(hd.loc[mask, 'Mã hóa đơn'])
    return int(round(float(ct.loc[ct['Mã hóa đơn'].isin(ids), 'Thành tiền_n'].sum())))


def in_month(y, m):
    s = pd.Timestamp(year=y, month=m, day=1)
    e = s + pd.offsets.MonthBegin(1)
    return ok & (hd['dt'] >= s) & (hd['dt'] < e)


def ids_of(mask):
    return set(hd.loc[mask, 'Mã hóa đơn'])


def lines_in(mask):
    return ct[ct['Mã hóa đơn'].isin(ids_of(mask))]


def find_sku(contains):
    """Look a product up in the catalogue by (accent-insensitive) name."""
    sp = t['sp']
    key = h.norm(contains)
    m = sp[sp['name_n'] == key]
    if m.empty:
        m = sp[sp['name_n'].str.contains(key, regex=False)]
    return m['Mã hàng'].iloc[0]


def unit_factors(code):
    """{ĐVT: số đơn vị cơ bản} for one product, base unit from stock report."""
    base = t['ton'].set_index('Mã hàng')['ĐVT'].to_dict().get(code)
    fac = {base: 1.0}
    for _, r in t['dv'][t['dv']['Mã hàng'] == code].iterrows():
        fac[r['ĐVT']] = float(r['qdoi'])
    return fac

end = pd.Timestamp('2025-06-29')
start = end - pd.Timedelta(days=6)
m = ok & (hd['dt'] >= start) & (hd['dt'] < end + pd.Timedelta(days=1))
RESULT = rev(m)
