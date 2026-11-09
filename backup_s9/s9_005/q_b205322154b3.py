import re, unicodedata
hd = DanhSachHoaDon.copy()
hd['date'] = parse_date(hd['Thời gian'])
st = hd['Trạng thái'].astype(str)
mm = (hd['date'].dt.year == 2025) & (hd['date'].dt.month == 2)
can = st[mm].str.contains('hủy|huỷ', case=False, na=False).sum()
tot = int(mm.sum())
RESULT = f"{round(can / tot * 100, 2):.2f}%"
