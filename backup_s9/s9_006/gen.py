"""Generate one solution file per question for retry9_006."""
import os
from pathlib import Path

OUT = Path('/tmp/s9_006')
OUT.mkdir(exist_ok=True)

PRE = '''import sys
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
'''

S = {}

S['q_36e95d0049de'] = '''
s, e = h.last_week('2025-12-09')
m = ok & (hd['dt'] >= s) & (hd['dt'] < e) & hd['dtt'].dt.hour.between(14, 21)
RESULT = rev(m)
'''

S['q_3a58e6f26cc8'] = '''
sub = lines_in(in_month(2025, 10))
cnt = sub.groupby('Mã hàng')['Mã hóa đơn'].nunique()
RESULT = int((cnt >= 112).sum())
'''

S['q_4a47fe6b7ab9'] = '''
sub = lines_in(in_month(2026, 2))
RESULT = int(round(float(sub['Thành tiền_n'].sum() - (sub['sl'] * sub['Giá vốn_n']).sum())))
'''

S['q_4d8826848736'] = '''
sub = hd[in_month(2025, 12)]
c = sub[sub['Mã KH'].notna() & (sub['Mã KH'].astype(str).str.strip() != '')]
c = c.groupby('Mã KH')['Mã hóa đơn'].nunique()
RESULT = int((c >= 3).sum())
'''

S['q_53b7fe7acdb7'] = '''
m = ok & (hd['dt'] >= pd.Timestamp('2026-04-01')) & (hd['dt'] < pd.Timestamp('2026-07-01'))
RESULT = rev(m)
'''

S['q_57ae63d15bbb'] = '''
sub = lines_in(in_month(2025, 5))
sub = sub[sub['Mã hàng'] == find_sku('Dầu ăn Simply 2L')]
RESULT = int(round(float(sub['Thành tiền_n'].sum())))
'''

S['q_61c8691e0eae'] = '''
m = ok & (hd['dt'] >= pd.Timestamp('2025-01-01')) & (hd['dt'] <= pd.Timestamp('2025-06-21'))
RESULT = int(hd.loc[m, 'Mã hóa đơn'].nunique())
'''

S['q_6765e6abcc6b'] = '''
ton = t['ton']
row = ton[ton['Mã hàng'] == find_sku('Bánh Oreo 133g')]  # base unit = gói
RESULT = int(round(float(row['Tồn cuối kỳ_n'].iloc[0])))
'''

S['q_71abc37384fd'] = '''
sub = lines_in(in_month(2025, 7))
RESULT = int(round(float(sub['Thành tiền_n'].sum() - (sub['sl'] * sub['Giá vốn_n']).sum())))
'''

S['q_745a5b81c65b'] = '''
m = in_month(2025, 10) & hd['dtt'].dt.hour.between(14, 21)
RESULT = int(len(ids_of(m)))
'''

S['q_834b2d633fc5'] = '''
ctn, nhap = t['ctn'], t['nhap']
code = find_sku('Giấy vệ sinh Pulppy 10 cuộn')
b = ctn[ctn['Mã hàng'] == code].merge(nhap[['Mã nhập hàng', 'dt', 'Trạng thái']], on='Mã nhập hàng')
b = b[(b['dt'] >= pd.Timestamp('2025-11-01')) & (b['dt'] < pd.Timestamp('2025-12-01'))]
b = b[~b['Trạng thái'].astype(str).str.contains('huỷ|hủy', case=False, na=False)]
fac = unit_factors(code)
b['base_qty'] = b['sl'] * b['ĐVT'].map(fac).fillna(1)
per_thung = b['base_qty'] / fac['thùng']
RESULT = int(round(float((b['sl'] * b['Đơn giá_n']).sum() / per_thung.sum())))
'''

S['q_873ed1cebdd9'] = '''
kh = t['kh']
si = set(kh.loc[kh['Nhóm khách hàng'].astype(str).str.strip() == 'sỉ', 'Mã khách hàng'])
m = in_month(2026, 7) & hd['Mã KH'].isin(si)
RESULT = rev(m)
'''

S['q_89444ae7458f'] = '''
s, e = h.last_week('2025-01-28')
m = ok & (hd['dt'] >= s) & (hd['dt'] < e) & hd['dtt'].dt.hour.between(6, 13)
RESULT = rev(m)
'''

S['q_8f39454cd859'] = '''
day = pd.Timestamp('2026-03-09')
m = hd['dt'].dt.normalize() == day
sub = ct[ct['Mã hóa đơn'].isin(ids_of(m))]
sub = sub[sub['Mã hàng'] == find_sku('Nước suối Aquafina 500ml')]
# unit price for ONE base unit (chai), before line discount
up = sub['Đơn giá_n'] / (sub['slqd'] / sub['sl'])
RESULT = int(round(float(up.mode().iloc[0])))
'''

S['q_8fc2669fa05d'] = '''
quy = t['quy']
credit = hd[(hd['Phương thức thanh toán'].astype(str) == 'Ghi nợ') & (hd['st_norm'] != 'cancel')][['Mã hóa đơn', 'dt']]
q = quy.merge(credit, on='Mã hóa đơn')
q = q[(q['dt_x'] >= pd.Timestamp('2025-10-01')) & (q['dt_x'] < pd.Timestamp('2025-11-01'))]
q = q[q['dt_x'].dt.normalize() > q['dt_y'].dt.normalize()]
RESULT = int(round(float(q['Giá trị_n'].sum())))
'''

S['q_9265fdb4154b'] = '''
sub = lines_in(in_month(2026, 4))
sub = sub[sub['Mã hàng'] == find_sku('Nếp cái hoa vàng')]  # base = kg
RESULT = int(round(float(sub['slqd'].sum())))
'''

S['q_9f6345476069'] = '''
sub = hd[in_month(2026, 4)]
c = sub[sub['Mã KH'].notna() & (sub['Mã KH'].astype(str).str.strip() != '')]
c = c.groupby('Mã KH')['Mã hóa đơn'].nunique()
RESULT = int((c >= 3).sum())
'''

S['q_ad5c8361bba1'] = '''
sub = lines_in(in_month(2026, 5))
sub = sub[sub['Mã hàng'] == find_sku('Mì Hảo Hảo tôm chua cay')]
RESULT = int(round(float(sub['Thành tiền_n'].sum())))
'''

S['q_b0473489a10c'] = '''
quy = t['quy']
credit = hd[(hd['Phương thức thanh toán'].astype(str) == 'Ghi nợ') & (hd['st_norm'] != 'cancel')][['Mã hóa đơn', 'dt']]
q = quy.merge(credit, on='Mã hóa đơn')
q = q[(q['dt_x'] >= pd.Timestamp('2026-08-01')) & (q['dt_x'] < pd.Timestamp('2026-08-06'))]
q = q[q['dt_x'].dt.normalize() > q['dt_y'].dt.normalize()]
RESULT = int(round(float(q['Giá trị_n'].sum())))
'''

S['q_bea7897a0242'] = '''
m = in_month(2026, 5) & hd['dtt'].dt.hour.between(6, 13)
RESULT = rev(m)
'''

S['q_c46ca1c8f9f4'] = '''
end = pd.Timestamp('2025-06-29')
start = end - pd.Timedelta(days=6)
m = ok & (hd['dt'] >= start) & (hd['dt'] < end + pd.Timedelta(days=1))
RESULT = rev(m)
'''

S['q_cc99936968b3'] = '''
m = ok & (hd['dt'].dt.normalize() == pd.Timestamp('2026-05-02'))
RESULT = int(len(ids_of(m)))
'''

S['q_d22396dcf9f2'] = '''
m = ok & (hd['dt'].dt.normalize() == pd.Timestamp('2026-03-02'))
RESULT = int(len(ids_of(m)))
'''

S['q_e1805ac91273'] = '''
ctn, nhap = t['ctn'], t['nhap']
code = find_sku('Nước lau sàn Sunlight 1L')
b = ctn[ctn['Mã hàng'] == code].merge(nhap[['Mã nhập hàng', 'dt', 'Trạng thái']], on='Mã nhập hàng')
b = b[(b['dt'] >= pd.Timestamp('2025-02-01')) & (b['dt'] < pd.Timestamp('2025-03-01'))]
b = b[~b['Trạng thái'].astype(str).str.contains('huỷ|hủy', case=False, na=False)]
fac = unit_factors(code)
b['base_qty'] = b['sl'] * b['ĐVT'].map(fac).fillna(1)
per_thung = b['base_qty'] / fac['thùng']
RESULT = int(round(float((b['sl'] * b['Đơn giá_n']).sum() / per_thung.sum())))
'''

S['q_e3c385351d76'] = '''
m = in_month(2025, 5) & (hd['Người bán'].astype(str).str.strip() == 'NV002')
RESULT = rev(m)
'''

for qid, body in S.items():
    (OUT / f'{qid}.py').write_text(PRE + body)
    print('wrote', qid)
