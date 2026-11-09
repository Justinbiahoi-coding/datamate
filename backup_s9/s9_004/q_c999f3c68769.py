import unicodedata, re, math
df = SoBanHang.copy()
df['dt'] = parse_date(df.ngay_ban)
st = df['Trạng thái xử lý'].astype(str).str.lower()
df = df[~st.str.contains('hủy|huỷ|cancel|trả|không giao được')].copy()
df['tot'] = to_num(df['Tổng tiền'])
df['sl'] = to_num(df['Số lượng'])
df['sl_le'] = to_num(df['Số lượng lẻ'])
df['nm'] = df['Nội dung'].map(lambda s: re.sub(r'\s+',' ',unicodedata.normalize('NFC',str(s))).strip().casefold())
def per(d,a,b): return d[(d['dt']>=a)&(d['dt']<=b)]
def rd(x): return int(math.floor(x+0.5))

x = per(df, '2025-03-01', '2025-03-31')
m = x['nm'].str.contains('nếp cái hoa vàng')
RESULT = int(x.loc[m, 'sl_le'].sum())
