import re, unicodedata
D = data['DuLieuBanHang']
hd = D['DanhSachHoaDon'].copy()
hd['date'] = parse_date(hd['Thời gian'])
st = hd['Trạng thái'].astype(str)
m = (hd['date'].dt.year == 2026) & (hd['date'].dt.month == 7)
RESULT = int(st[m].str.contains('hủy|huỷ', case=False, na=False).sum())
