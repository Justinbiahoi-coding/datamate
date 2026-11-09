import re, unicodedata
hd = DanhSachHoaDon.copy()
def norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFD', str(s)).encode('ascii','ignore').decode().lower()).strip()
hd['date'] = parse_date(hd['Thời gian'])
st = hd['Trạng thái'].astype(str)
hd['valid'] = ~(st.str.contains('hủy|huỷ', case=False, na=False) | st.str.contains('trả hàng|hoàn hàng|trả lại', case=False, na=False))
hd['rev'] = to_num(hd['Tổng tiền hàng'])
m = hd['valid'] & (hd['date'].dt.year == 2025) & (hd['date'].dt.month == 2)
s = hd[m]
RESULT = int(s['rev'].sum() / len(s) + 0.5)
