import re, unicodedata
hd = DanhSachHoaDon.copy()
ct = DanhSachHoaDonChiTiet.copy()
def norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFD', str(s)).encode('ascii','ignore').decode().lower()).strip()
hd['date'] = parse_date(hd['Thời gian'])
st = hd['Trạng thái'].astype(str)
hd['valid'] = ~(st.str.contains('hủy|huỷ', case=False, na=False) | st.str.contains('trả hàng|hoàn hàng|trả lại', case=False, na=False))
ordv = hd.set_index('Mã hóa đơn')['valid']
ordd = hd.set_index('Mã hóa đơn')['date']
ct['_valid'] = ct['Mã hóa đơn'].map(ordv).fillna(False).astype(bool)
ct['_date'] = ct['Mã hóa đơn'].map(ordd)
m = (ct['Tên hàng'].apply(norm) == 'nep cai hoa vang') & ct['_valid'] & (ct['_date'].dt.year == 2025) & (ct['_date'].dt.month == 9)
RESULT = int(to_num(ct.loc[m, 'Số lượng quy đổi']).sum())
