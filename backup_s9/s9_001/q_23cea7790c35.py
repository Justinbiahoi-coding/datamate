import unicodedata, re, math
def money(x):
    if pd.isna(x): return float('nan')
    if isinstance(x,(int,float)): return float(x)
    s=str(x).strip().lower().replace('đ','').replace('₫','').replace(' ','')
    m=re.fullmatch(r'(-?)(\d+)tr(\d*)',s)
    if m: return (-1 if m.group(1) else 1)*(int(m.group(2))*1e6+(int(m.group(3).ljust(3,'0'))*1e3 if m.group(3) else 0))
    m=re.fullmatch(r'(-?)([\d.,]+)tr',s)
    if m: return (-1 if m.group(1) else 1)*float(m.group(2).replace(',','.'))*1e6
    m=re.fullmatch(r'(-?)([\d.,]+)k',s)
    if m: return (-1 if m.group(1) else 1)*float(m.group(2).replace(',','.'))*1e3
    if re.fullmatch(r'-?\d{1,3}(,\d{3})*(\.\d+)?',s) and ',' in s: return float(s.replace(',',''))
    if re.fullmatch(r'-?\d{1,3}(\.\d{3})+',s): return float(s.replace('.',''))
    return float(s.replace(',',''))

h = DanhSachHoaDon.drop_duplicates('Mã hóa đơn').copy()
h['dt'] = parse_date(h['Thời gian'])
h = h[~h['Trạng thái'].str.contains('hủy|huỷ|trả|hoàn trả', case=False, na=False)]

c = pd.concat([DanhSachHoaDonChiTiet_1, DanhSachHoaDonChiTiet_2], ignore_index=True).drop_duplicates(['Mã hóa đơn','STT'])
c['v'] = c['Thành tiền'].map(money)
c = c.merge(h[['Mã hóa đơn','dt']], on='Mã hóa đơn')
c['nm'] = c['Tên hàng'].map(lambda s: re.sub(r'\s+',' ',unicodedata.normalize('NFC',str(s))).strip().casefold())
def per(df,a,b): return df[(df['dt']>=a)&(df['dt']<=b)]
def rd(x): return int(math.floor(x+0.5))

h_debt = DanhSachHoaDon.drop_duplicates('Mã hóa đơn').copy()
h_debt = h_debt[~h_debt['Trạng thái'].astype(str).str.contains('hủy|huỷ|cancel', case=False, na=False)]
h_debt = h_debt[h_debt['Phương thức thanh toán'] != 'Thu hộ (COD)']
h_debt = h_debt[h_debt['Mã KH'].notna()]
h_debt['d'] = parse_date(h_debt['Thời gian'])
# Đã đặt quá 7 ngày: đặt trước 2025-04-05 trừ 7 ngày = trước 2025-03-29
cutoff = pd.Timestamp(as_of_date) - pd.Timedelta(days=7)
h_debt = h_debt[h_debt['d'] < cutoff]
h_debt['tot'] = to_num(h_debt['Tổng sau giảm giá'])

sq = SoQuy.copy()
sq['v'] = sq['Giá trị'].map(money)
sq['t'] = parse_date(sq['Thời gian'])
sq = sq[sq['t'] <= pd.Timestamp(as_of_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]
paid = sq.groupby('Mã hóa đơn')['v'].sum()
h_debt['owe'] = h_debt['tot'] - h_debt['Mã hóa đơn'].map(paid).fillna(0)
RESULT = int(round(h_debt.loc[h_debt['owe'] > 0, 'owe'].sum()))
