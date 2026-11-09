import re, unicodedata
hd = DanhSachHoaDon.copy()
def norm(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFD', str(s)).encode('ascii','ignore').decode().lower()).strip()
hd['date'] = parse_date(hd['Thời gian'])
st = hd['Trạng thái'].astype(str)
hd['valid'] = ~(st.str.contains('hủy|huỷ', case=False, na=False) | st.str.contains('trả hàng|hoàn hàng|trả lại', case=False, na=False))
hd['rev'] = to_num(hd['Tổng tiền hàng'])
grp = DanhSachKhachHang.set_index('Mã khách hàng')['Nhóm khách hàng']
hd['nhom'] = hd['Mã KH'].map(grp)
m = hd['valid'] & (hd['date'].dt.year == 2025) & (hd['date'].dt.month == 1) & (hd['nhom'] == 'sỉ')
RESULT = int(hd.loc[m, 'rev'].sum())
