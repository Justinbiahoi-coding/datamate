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

x = per(df, as_of_date, as_of_date)
RESULT = int(x['tot'].sum())
