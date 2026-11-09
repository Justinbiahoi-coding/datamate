import unicodedata, re, math
nh = DanhSachNhapHang.copy()
nh['d'] = pd.to_datetime(nh['Thời gian'], format='%d/%m/%Y', errors='coerce')
nh = nh[~nh['Trạng thái'].astype(str).str.contains('hủy|huỷ', case=False, na=False)]
nh_june = nh[(nh.d >= '2025-06-01') & (nh.d <= '2025-06-30') & (nh['Mã NCC'] == 'NCC002')]

ct = DanhSachChiTietNhapHang[DanhSachChiTietNhapHang['Mã nhập hàng'].isin(nh_june['Mã nhập hàng'])].copy()
ct = ct.merge(DanhSachSanPham[['Mã hàng', 'Tên hàng']], on='Mã hàng')
m = ct['Tên hàng'].str.lower().str.contains('omo') & (ct['ĐVT'].str.lower() == 'thùng')
sub = ct[m].copy()
sub['sl'] = to_num(sub['Số lượng'])
sub['dg'] = to_num(sub['Đơn giá'])
RESULT = int(round((sub['sl'] * sub['dg']).sum() / sub['sl'].sum()))
