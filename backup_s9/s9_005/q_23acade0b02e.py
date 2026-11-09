import re, unicodedata
D = data['DuLieuBanHang']
hd = D['DanhSachHoaDon'].copy()
sq = D['SoQuy'].copy()
hd['date'] = parse_date(hd['Thời gian'])
st = hd['Trạng thái'].astype(str)
hd['valid'] = ~(st.str.contains('hủy|huỷ', case=False, na=False) | st.str.contains('trả hàng|hoàn hàng|trả lại', case=False, na=False))
sq['pdate'] = pd.to_datetime(sq['Thời gian'], errors='coerce')
orders = hd[['Mã hóa đơn', 'date', 'valid', 'Phương thức thanh toán']].rename(
    columns={'date': 'odate', 'Phương thức thanh toán': 'order_pt'})
mg = sq.merge(orders, on='Mã hóa đơn', how='left')
m = (mg['order_pt'] == 'Ghi nợ') & mg['valid'].fillna(False).astype(bool) & \
    (mg['pdate'].dt.year == 2026) & (mg['pdate'].dt.month == 6) & \
    (mg['pdate'].dt.normalize() > mg['odate'])
RESULT = int(to_num(mg.loc[m, 'Giá trị']).sum())
