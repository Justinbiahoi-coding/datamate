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
h_clean = h[~h['Trạng thái'].str.contains('hủy|huỷ|trả|hoàn trả', case=False, na=False)].copy()

c = pd.concat([DanhSachHoaDonChiTiet_1, DanhSachHoaDonChiTiet_2], ignore_index=True).drop_duplicates(['Mã hóa đơn','STT'])
c['v'] = c['Thành tiền'].map(money)
c['cost'] = c['Giá vốn'].map(money)
c['sl'] = to_num(c['Số lượng'])
c['sl_qd'] = to_num(c['Số lượng quy đổi'])

c = c.merge(h_clean[['Mã hóa đơn','dt']], on='Mã hóa đơn')
c['nm'] = c['Tên hàng'].map(lambda s: re.sub(r'\s+',' ',unicodedata.normalize('NFC',str(s))).strip().casefold())
def per(df,a,b): return df[(df['dt']>=a)&(df['dt']<=b)]
def rd(x): return int(math.floor(x+0.5))

x = per(c, '2025-07-01', '2025-09-30')
RESULT = int(x['Mã hóa đơn'].nunique())
