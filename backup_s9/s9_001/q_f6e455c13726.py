import unicodedata, re, math
d = pd.concat([SoBanHang_1__all, SoBanHang_2026__all], ignore_index=True)
d = d[d['Mã hóa đơn'].notna()].copy()
d = d.drop_duplicates()
def money(s):
    s = unicodedata.normalize('NFC',str(s)).strip().lower().replace('đ','').replace(' ','')
    if s in ('','nan','none'): return float('nan')
    neg = s.startswith('-'); s = s.lstrip('-')
    if s.endswith('k'): v = float(s[:-1].replace(',','.'))*1000
    else: v = float(s.replace('.','').replace(',',''))
    return -v if neg else v
d['amt'] = d['Trị giá'].map(money)
d['dt'] = parse_date(d['Ngày giao dịch'])
d['nm'] = d['Hàng'].map(lambda s: re.sub(r'\s+',' ',unicodedata.normalize('NFC',str(s))).strip().casefold())
st = d['Status'].map(lambda s: unicodedata.normalize('NFC',str(s)).lower())
d['bad'] = st.str.contains('hủy|huỷ|trả')|(d['so_luong']<0)
badord = set(d.loc[d['bad'],'Mã hóa đơn'])
ok = d[~d['Mã hóa đơn'].isin(badord)].copy()
def per(df,a,b): return df[(df['dt']>=a)&(df['dt']<=b)]
def rd(x): return int(math.floor(x+0.5))

start_date = (pd.to_datetime(as_of_date) - pd.Timedelta(days=29)).strftime('%Y-%m-%d')
x = per(ok, start_date, as_of_date)
RESULT = int(x['Mã hóa đơn'].nunique())
