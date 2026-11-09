import re, unicodedata
from collections import Counter
D = data['DuLieuBanHang']
hd = D['DanhSachHoaDon'].copy()
ct = data['DanhSachHoaDonChiTiet'].copy()
def norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFD', str(s)).encode('ascii','ignore').decode().lower()).strip()
hd['date'] = parse_date(hd['Thời gian'])
ct['_date'] = ct['Mã hóa đơn'].map(hd.set_index('Mã hóa đơn')['date'])
m = ct['Tên hàng'].apply(norm).str.contains('bobby', na=False) & (ct['_date'] == pd.Timestamp('2025-07-23'))
fac = {'gói': 1.0, 'thùng': 4.0, 'lốc': 1.0}
vals = []
for _, r in ct.loc[m].iterrows():
    f = fac.get(str(r['Đơn vị tính']).strip(), 1.0)
    vals.append(float(str(r['Đơn giá']).replace(',', '')) / f)
RESULT = int(Counter(vals).most_common(1)[0][0]) if vals else 'unanswerable'
