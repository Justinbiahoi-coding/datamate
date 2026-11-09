import re, unicodedata
hd = DanhSachHoaDon.copy()
hd['date'] = parse_date(hd['Thời gian'])
st = hd['Trạng thái'].astype(str)
m = (hd['date'].dt.year == 2025) & (hd['date'].dt.month == 10)
RESULT = int(st[m].str.contains('hủy|huỷ', case=False, na=False).sum())
