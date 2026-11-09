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

bg = BangGia.copy()
bg['dt'] = parse_date(bg['Ngày áp dụng'])
bg['nm'] = bg['ten_hang'].map(lambda s: unicodedata.normalize('NFC',str(s)).strip().casefold())
m = bg['nm'].str.contains('cà phê sữa') & bg['nm'].str.contains(r'\(l\)|\bl\b') & (bg['dt'] <= '2025-06-10')
sub = bg[m].sort_values('dt')
RESULT = int(money(sub.iloc[-1]['Giá mới']))
