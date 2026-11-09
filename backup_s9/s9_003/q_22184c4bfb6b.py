import unicodedata, re, math
df = SoBanHang.copy()
df['dt'] = parse_date(df.ngay_ban)
st = df['Trạng thái xử lý'].astype(str).str.lower()
df = df[~st.str.contains('hủy|huỷ|cancel|trả|không giao được')].copy()
df['nm'] = df['Nội dung'].map(lambda s: re.sub(r'\s+',' ',unicodedata.normalize('NFC',str(s))).strip().casefold())

alp = df[df['nm'].str.contains('alpenliebe') & (df.dt <= '2025-04-15')].sort_values('dt')
val_str = str(alp.iloc[-1]['don_gia']).replace(',', '').replace('.', '').replace('đ', '').strip()
RESULT = int(float(val_str))
