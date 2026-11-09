import unicodedata, re, math
h = DanhSachHoaDon.drop_duplicates('Mã hóa đơn').copy()
h['dt'] = pd.to_datetime(h['Thời gian'], dayfirst=True)
h = h[~h['Trạng thái'].astype(str).str.contains('hủy|huỷ|trả', case=False, na=False)].copy()

c = DanhSachHoaDonChiTiet.drop_duplicates(['Mã hóa đơn', 'STT']).copy()
c = c.merge(h[['Mã hóa đơn', 'dt']], on='Mã hóa đơn')
c['nm'] = c['Tên hàng'].map(lambda s: re.sub(r'\s+',' ',unicodedata.normalize('NFC',str(s))).strip().casefold())

m = c['nm'].str.contains('hảo hảo tôm chua cay') & (c.dt <= '2026-04-21')
sub = c[m].sort_values('dt')
val_str = str(sub.iloc[-1]['Đơn giá']).replace(',', '').replace('.', '').replace('đ', '').strip()
RESULT = int(float(val_str))
