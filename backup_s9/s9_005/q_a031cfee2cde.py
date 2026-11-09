import re, unicodedata
nh = DanhSachNhapHang.copy()
nh['date'] = parse_date(nh['Thời gian'])
nh['amt'] = to_num(nh['Cần trả NCC'])
st = nh['Trạng thái'].astype(str)
bad = st.str.contains('hủy|huỷ', case=False, na=False)
m = (nh['date'].dt.year == 2025) & (nh['date'].dt.month == 1) & ~bad
RESULT = int(nh.loc[m, 'amt'].sum())
