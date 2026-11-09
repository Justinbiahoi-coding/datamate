import re, unicodedata
D = data['DuLieuBanHang']
hd = D['DanhSachHoaDon'].copy()
hd['date'] = parse_date(hd['Thời gian'])
st = hd['Trạng thái'].astype(str)
hd['valid'] = ~(st.str.contains('hủy|huỷ', case=False, na=False) | st.str.contains('trả hàng|hoàn hàng|trả lại', case=False, na=False))
hd['hour'] = hd['Thời gian tạo'].dt.hour
m = hd['valid'] & (hd['date'].dt.year == 2025) & (hd['date'].dt.month == 9) & (hd['hour'] >= 6) & (hd['hour'] < 14)
RESULT = int(m.sum())
