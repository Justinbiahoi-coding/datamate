import re, unicodedata
hd = DanhSachHoaDon.copy()
hd['date'] = parse_date(hd['Thời gian'])
st = hd['Trạng thái'].astype(str)
hd['valid'] = ~(st.str.contains('hủy|huỷ', case=False, na=False) | st.str.contains('trả hàng|hoàn hàng|trả lại', case=False, na=False))
hd['rev'] = to_num(hd['Tổng tiền hàng'])
m = hd['valid'] & (hd['date'].dt.year == 2026) & (hd['date'].dt.month == 4)
s = hd[m]
RESULT = int(s['rev'].sum() / len(s) + 0.5)
