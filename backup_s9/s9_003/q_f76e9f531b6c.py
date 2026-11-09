import unicodedata, re, math
h = DanhSachHoaDon.drop_duplicates('Mã hóa đơn').copy()
h['dt'] = parse_date(h['Thời gian'])
h_clean = h[~h['Trạng thái'].str.contains('hủy|huỷ|trả|hoàn trả', case=False, na=False)].copy()

c = pd.concat([DanhSachHoaDonChiTiet_1, DanhSachHoaDonChiTiet_2], ignore_index=True).drop_duplicates(['Mã hóa đơn','STT'])
c = c.merge(h_clean[['Mã hóa đơn','dt']], on='Mã hóa đơn')
c['nm'] = c['Tên hàng'].map(lambda s: re.sub(r'\s+',' ',unicodedata.normalize('NFC',str(s))).strip().casefold())
c['sl_qd'] = to_num(c['Số lượng quy đổi'])

x = c[(c['dt'] >= '2026-03-01') & (c['dt'] <= '2026-03-31')]
m = x['nm'].str.contains('tiramisu')
RESULT = int(x.loc[m, 'sl_qd'].sum())
