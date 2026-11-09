import re, unicodedata
D = data['DuLieuBanHang']
hd = D['DanhSachHoaDon'].copy()
ct = data['DanhSachHoaDonChiTiet'].copy()
hd['date'] = parse_date(hd['Thời gian'])
st = hd['Trạng thái'].astype(str)
hd['valid'] = ~(st.str.contains('hủy|huỷ', case=False, na=False) | st.str.contains('trả hàng|hoàn hàng|trả lại', case=False, na=False))
ordv = hd.set_index('Mã hóa đơn')['valid']
ordd = hd.set_index('Mã hóa đơn')['date']
ct['_valid'] = ct['Mã hóa đơn'].map(ordv).fillna(False).astype(bool)
ct['_date'] = ct['Mã hóa đơn'].map(ordd)
m = ct['_valid'] & (ct['_date'].dt.year == 2026) & (ct['_date'].dt.month == 3)
cnt = ct[m].groupby('Mã hàng')['Mã hóa đơn'].nunique()
RESULT = int((cnt >= 84).sum())
