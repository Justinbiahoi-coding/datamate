import unicodedata, re, math
h = DanhSachHoaDon.drop_duplicates('Mã hóa đơn').copy()
h['dt'] = parse_date(h['Thời gian'])
h['t_tao'] = parse_date(h['Thời gian tạo'])
h = h[~h['Trạng thái'].astype(str).str.contains('hủy|huỷ|trả', case=False, na=False)].copy()
h['tot'] = to_num(h['Tổng tiền hàng'])

c = DanhSachHoaDonChiTiet.drop_duplicates(['Mã hóa đơn', 'STT']).copy()
c['v'] = to_num(c['Thành tiền'])
c['sl'] = to_num(c['Số lượng'])
c['sl_qd'] = to_num(c['Số lượng quy đổi'])
c = c.merge(h[['Mã hóa đơn', 'dt', 't_tao', 'Kênh bán', 'Người bán']], on='Mã hóa đơn')
c['nm'] = c['Tên hàng'].map(lambda s: re.sub(r'\s+',' ',unicodedata.normalize('NFC',str(s))).strip().casefold())
def per(df,a,b): return df[(df['dt']>=a)&(df['dt']<=b)]
def rd(x): return int(math.floor(x+0.5))

nh = DanhSachNhapHang.copy()
nh['d'] = parse_date(nh['Thời gian'])
nh = nh[~nh['Trạng thái'].astype(str).str.contains('hủy|huỷ', case=False, na=False)]
nh_feb = nh[(nh.d >= '2026-02-01') & (nh.d <= '2026-02-28')]
RESULT = int(round(to_num(nh_feb['Cần trả NCC']).sum()))
