import unicodedata, re, math
h = DanhSachHoaDon.drop_duplicates('Mã hóa đơn').copy()
h['dt'] = pd.to_datetime(h['Thời gian'], dayfirst=True)
h = h[~h['Trạng thái'].astype(str).str.contains('hủy|huỷ|trả', case=False, na=False)].copy()
h['tot'] = to_num(h['Tổng tiền hàng'])

x = h[(h.dt >= '2025-03-01') & (h.dt <= '2025-03-31')]
m = x['Kênh bán'] == 'store'
RESULT = int(x.loc[m, 'tot'].sum())
