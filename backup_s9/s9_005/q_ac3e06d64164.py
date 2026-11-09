import re, unicodedata
from collections import Counter
hd = DanhSachHoaDon.copy()
ct = DanhSachHoaDonChiTiet.copy()
def norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFD', str(s)).encode('ascii','ignore').decode().lower()).strip()
hd['date'] = parse_date(hd['Thời gian'])
ct['_date'] = ct['Mã hóa đơn'].map(hd.set_index('Mã hóa đơn')['date'])
m = ct['Tên hàng'].apply(norm).str.contains('chinsu', na=False) & (ct['_date'] == pd.Timestamp('2026-02-17'))
fac = {'chai': 1.0, 'lốc': 6.0, 'thùng': 24.0}
vals = []
for _, r in ct.loc[m].iterrows():
    f = fac.get(str(r['Đơn vị tính']).strip(), 1.0)
    vals.append(float(str(r['Đơn giá']).replace(',', '')) / f)
RESULT = int(Counter(vals).most_common(1)[0][0]) if vals else 'unanswerable'
