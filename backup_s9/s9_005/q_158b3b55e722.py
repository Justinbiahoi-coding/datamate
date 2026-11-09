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
q = to_num(ct['Số lượng'])
amt = to_num(ct['Thành tiền'])
gv = to_num(ct['Giá vốn'])
m = ct['_valid'] & (ct['_date'].dt.year == 2025) & (ct['_date'].dt.month == 10)
RESULT = int(round(float(amt[m].sum() - (q[m] * gv[m]).sum())))
