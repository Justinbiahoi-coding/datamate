import json, subprocess, os, sys
from pathlib import Path

Path('/tmp/s9_001').mkdir(parents=True, exist_ok=True)

HEADER_105 = '''import unicodedata, re, math
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
d['nm'] = d['Hàng'].map(lambda s: re.sub(r'\\s+',' ',unicodedata.normalize('NFC',str(s))).strip().casefold())
st = d['Status'].map(lambda s: unicodedata.normalize('NFC',str(s)).lower())
d['bad'] = st.str.contains('hủy|huỷ|trả')|(d['so_luong']<0)
badord = set(d.loc[d['bad'],'Mã hóa đơn'])
ok = d[~d['Mã hóa đơn'].isin(badord)].copy()
def per(df,a,b): return df[(df['dt']>=a)&(df['dt']<=b)]
def rd(x): return int(math.floor(x+0.5))
'''

HEADER_106 = '''import unicodedata, re, math
def money(x):
    if pd.isna(x): return float('nan')
    if isinstance(x,(int,float)): return float(x)
    s=str(x).strip().lower().replace('đ','').replace('₫','').replace(' ','')
    m=re.fullmatch(r'(-?)(\\d+)tr(\\d*)',s)
    if m: return (-1 if m.group(1) else 1)*(int(m.group(2))*1e6+(int(m.group(3).ljust(3,'0'))*1e3 if m.group(3) else 0))
    m=re.fullmatch(r'(-?)([\\d.,]+)tr',s)
    if m: return (-1 if m.group(1) else 1)*float(m.group(2).replace(',','.'))*1e6
    m=re.fullmatch(r'(-?)([\\d.,]+)k',s)
    if m: return (-1 if m.group(1) else 1)*float(m.group(2).replace(',','.'))*1e3
    if re.fullmatch(r'-?\\d{1,3}(,\\d{3})*(\\.\\d+)?',s) and ',' in s: return float(s.replace(',',''))
    if re.fullmatch(r'-?\\d{1,3}(\\.\\d{3})+',s): return float(s.replace('.',''))
    return float(s.replace(',',''))

h = DanhSachHoaDon.drop_duplicates('Mã hóa đơn').copy()
h['dt'] = parse_date(h['Thời gian'])
h = h[~h['Trạng thái'].str.contains('hủy|huỷ|trả|hoàn trả', case=False, na=False)]

c = pd.concat([DanhSachHoaDonChiTiet_1, DanhSachHoaDonChiTiet_2], ignore_index=True).drop_duplicates(['Mã hóa đơn','STT'])
c['v'] = c['Thành tiền'].map(money)
c = c.merge(h[['Mã hóa đơn','dt']], on='Mã hóa đơn')
c['nm'] = c['Tên hàng'].map(lambda s: re.sub(r'\\s+',' ',unicodedata.normalize('NFC',str(s))).strip().casefold())
def per(df,a,b): return df[(df['dt']>=a)&(df['dt']<=b)]
def rd(x): return int(math.floor(x+0.5))
'''

solutions = {
    # 00: Từ 1/1 năm nay đến hết hnay đã bán đc bao nhiêu đơn? (as_of: 2026-04-17)
    'q_a1a58dc249cf': HEADER_105 + '''
x = per(ok, '2026-01-01', as_of_date)
RESULT = int(x['Mã hóa đơn'].nunique())
''',

    # 01: Trong tháng 5/2025, số ly size M bán đc là bao nhiêu, tính mọi loại đồ uống?
    'q_aa246e13cdb9': HEADER_105 + '''
x = per(ok, '2025-05-01', '2025-05-31')
m = x['nm'].str.contains(r'\\(m\\)|\\bm\\b') & (x['Unit'].str.lower() == 'ly')
RESULT = int(x.loc[m, 'so_luong'].sum())
''',

    # 02: Tháng 12/2025 quán bán ra tổng cộng mấy ly size L, cộng tất cả các món?
    'q_ab910254f626': HEADER_105 + '''
x = per(ok, '2025-12-01', '2025-12-31')
m = x['nm'].str.contains(r'\\(l\\)|\\bl\\b') & (x['Unit'].str.lower() == 'ly')
RESULT = int(x.loc[m, 'so_luong'].sum())
''',

    # 03: Có mấy ngày trong tháng 2/2025 cửa hàng bán đc từ 10.000.000 đồng trở lên
    'q_bab2bec0be28': HEADER_105 + '''
x = per(ok, '2025-02-01', '2025-02-28')
day_sum = x.groupby('dt').amt.sum()
RESULT = int((day_sum >= 10000000).sum())
''',

    # 04: Cho hỏi tháng 3/2025 bán ra bao nhiêu ly Sinh tố xoài (L)?
    'q_c2fc8ca094e5': HEADER_105 + '''
x = per(ok, '2025-03-01', '2025-03-31')
m = x['nm'].str.contains('sinh tố xoài') & x['nm'].str.contains(r'\\(l\\)|\\bl\\b')
RESULT = int(x.loc[m, 'so_luong'].sum())
''',

    # 05: cho tôi biết dthu tháng 2/2025
    'q_c625c2207845': HEADER_105 + '''
x = per(ok, '2025-02-01', '2025-02-28')
RESULT = int(x.amt.sum())
''',

    # 06: ca chieu tuan roi dthu duoc bao nhieu (as_of: 2026-04-05, Sunday -> 2026-03-23..2026-03-29)
    'q_ca9498a0ddb3': HEADER_105 + '''
# as_of: 2026-04-05 (Sunday, weekday=6)
# Monday this week: 2026-03-30
# Monday last week: 2026-03-23..2026-03-29
x = per(ok, '2026-03-23', '2026-03-29')
first_hours = x.groupby('Mã hóa đơn')['Giờ'].first()
first_hours_dt = pd.to_datetime(first_hours)
afternoon_orders = set(first_hours[first_hours_dt.dt.hour.between(14, 21)].index)
RESULT = int(x[x['Mã hóa đơn'].isin(afternoon_orders)].amt.sum())
''',

    # 07: Doanh thu tháng 9/2025 bao nhiêu vậy?
    'q_da1e65bdc743': HEADER_105 + '''
x = per(ok, '2025-09-01', '2025-09-30')
RESULT = int(x.amt.sum())
''',

    # 08: Tháng 2/2025 giá nhập bình quân một hộp Bánh tiramisu là bao nhiêu?
    'q_df2c3f7132ac': HEADER_105 + '''
nh = SoNhapHang.copy()
nh['d'] = parse_date(nh['Ngày nhập'])
nh['nm'] = nh['Tên mặt hàng'].map(lambda s: re.sub(r'\\s+',' ',unicodedata.normalize('NFC',str(s))).strip().casefold())
nh['tt'] = nh['Thành tiền'].map(money)
nh['sl'] = to_num(nh['SL nhập'])
m = nh['nm'].str.contains('tiramisu') & (nh.d >= '2025-02-01') & (nh.d <= '2025-02-28')
RESULT = rd(nh.loc[m, 'tt'].sum() / nh.loc[m, 'sl'].sum())
''',

    # 09: Cho hỏi trung bình mỗi đơn tháng 3/2026 mang về bao nhiêu doanh thu?
    'q_e40f683db005': HEADER_105 + '''
x = per(ok, '2026-03-01', '2026-03-31')
RESULT = rd(x.groupby('Mã hóa đơn').amt.sum().mean())
''',

    # 10: tháng 4/2026 cửa hàng bán dduwowcj tổng cộng bao nhieeu tiền
    'q_ea0e86f37bab': HEADER_105 + '''
x = per(ok, '2026-04-01', '2026-04-30')
RESULT = int(x.amt.sum())
''',

    # 11: tổng dthu 30 ngày gần nhất là bao nhiêu (as_of: 2026-06-05)
    'q_eba1987c1f68': HEADER_105 + '''
# 30 ngày gần nhất tính đến as_of_date:
start_date = (pd.to_datetime(as_of_date) - pd.Timedelta(days=29)).strftime('%Y-%m-%d')
x = per(ok, start_date, as_of_date)
RESULT = int(x.amt.sum())
''',

    # 12: tháng này cửa hàng bỏ ra bao nhiu tiền nhập hàng (as_of: 2026-06-24)
    'q_ebe4f9b3e3b7': HEADER_105 + '''
nh = SoNhapHang.copy()
nh['d'] = parse_date(nh['Ngày nhập'])
nh['tt'] = nh['Thành tiền'].map(money)
m = (nh.d >= '2026-06-01') & (nh.d <= as_of_date)
RESULT = int(nh.loc[m, 'tt'].sum())
''',

    # 13: Tháng 2/2026 có mấy đơn có dthu từ 130.000 đồng trở lên?
    'q_f1c5c01b78e0': HEADER_105 + '''
x = per(ok, '2026-02-01', '2026-02-28')
g = x.groupby('Mã hóa đơn').amt.sum()
RESULT = int((g >= 130000).sum())
''',

    # 14: cho hoir giá bán một ly cà phê sữa (l) vào ngày 10/06/2025 laf bnhiu
    'q_f321dd447d00': HEADER_105 + '''
bg = BangGia.copy()
bg['dt'] = parse_date(bg['Ngày áp dụng'])
bg['nm'] = bg['ten_hang'].map(lambda s: unicodedata.normalize('NFC',str(s))).strip().casefold()
m = bg['nm'].str.contains('cà phê sữa') & bg['nm'].str.contains(r'\\(l\\)|\\bl\\b') & (bg['dt'] <= '2025-06-10')
sub = bg[m].sort_values('dt')
RESULT = int(money(sub.iloc[-1]['Giá mới']))
''',

    # 15: 30 ngày gần nhất có tổng cộng bao nhiêu đơn? (as_of: 2025-11-12)
    'q_f6e455c13726': HEADER_105 + '''
start_date = (pd.to_datetime(as_of_date) - pd.Timedelta(days=29)).strftime('%Y-%m-%d')
x = per(ok, start_date, as_of_date)
RESULT = int(x['Mã hóa đơn'].nunique())
''',

    # 16: xem giup so don bi huy trong thang 6 nam 2025 la bao nhieu
    'q_f7ddc2a17849': HEADER_105 + '''
m6 = per(d, '2025-06-01', '2025-06-30')
m6_st = m6['Status'].map(lambda s: unicodedata.normalize('NFC',str(s)).lower())
canc = set(m6.loc[m6_st.str.contains('hủy|huỷ'), 'Mã hóa đơn'])
RESULT = len(canc)
''',

    # 17: giá trị trung bình một đơn tháng 3/2025 là bao nhiêu ta
    'q_fe699a7dc387': HEADER_105 + '''
x = per(ok, '2025-03-01', '2025-03-31')
RESULT = rd(x.groupby('Mã hóa đơn').amt.sum().mean())
''',

    # 18: (biz_106) Tháng 5/2025 cửa hàng bán đc tổng cộng bao nhiêu tiền?
    'q_00c4e64fe706': HEADER_106 + '''
x = per(c, '2025-05-01', '2025-05-31')
RESULT = int(x.v.sum())
''',

    # 19: (biz_106) Tháng 5/2026 giá nhập bình quân một hộp Bánh croissant là bao nhiêu vậy?
    'q_0266c6b24cbf': HEADER_106 + '''
nh = DanhSachNhapHang.copy()
nh['d'] = parse_date(nh['Thời gian'])
nh = nh[~nh['Trạng thái'].astype(str).str.contains('hủy|huỷ', case=False, na=False)]
nh_may = nh[(nh.d >= '2026-05-01') & (nh.d <= '2026-05-31')]
ct = DanhSachChiTietNhapHang[DanhSachChiTietNhapHang['Mã nhập hàng'].isin(nh_may['Mã nhập hàng'])].copy()
ct = ct.merge(DanhSachSanPham[['Mã hàng','Tên hàng']], on='Mã hàng')
ct['nm'] = ct['Tên hàng'].map(lambda s: unicodedata.normalize('NFC',str(s)).strip().casefold())
m = ct['nm'].str.contains('croissant')
ct_cro = ct[m]
ct_cro['tt'] = to_num(ct_cro['Số lượng']) * ct_cro['Đơn giá'].map(money)
RESULT = rd(ct_cro['tt'].sum() / to_num(ct_cro['Số lượng']).sum())
''',

    # 20: (biz_106) Xem giúp khách còn nợ cửa hàng tổng cộng bao nhiêu tính đến hết ngày 20/09/2025? (as_of: 2025-09-20)
    'q_073aee886aef': HEADER_106 + '''
h_debt = DanhSachHoaDon.drop_duplicates('Mã hóa đơn').copy()
h_debt = h_debt[~h_debt['Trạng thái'].astype(str).str.contains('hủy|huỷ|cancel', case=False, na=False)]
h_debt = h_debt[h_debt['Phương thức thanh toán'] != 'Thu hộ (COD)']
h_debt = h_debt[h_debt['Mã KH'].notna()]
h_debt['d'] = parse_date(h_debt['Thời gian'])
h_debt = h_debt[h_debt['d'] <= pd.Timestamp(as_of_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]
h_debt['tot'] = to_num(h_debt['Tổng sau giảm giá'])

sq = SoQuy.copy()
sq['v'] = sq['Giá trị'].map(money)
sq['t'] = parse_date(sq['Thời gian'])
sq = sq[sq['t'] <= pd.Timestamp(as_of_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]
paid = sq.groupby('Mã hóa đơn')['v'].sum()
h_debt['owe'] = h_debt['tot'] - h_debt['Mã hóa đơn'].map(paid).fillna(0)
RESULT = int(round(h_debt.loc[h_debt['owe'] > 0, 'owe'].sum()))
''',

    # 21: (biz_106) Tổng dthu tháng 2 năm 2025 là bao nhiêu?
    'q_09ae9e282fd3': HEADER_106 + '''
x = per(c, '2025-02-01', '2025-02-28')
RESULT = int(x.v.sum())
''',

    # 22: (biz_106) trong thang 2 nam 2025 cua hang ban duoc may ly tra sua o long (m)
    'q_0d5667212f41': HEADER_106 + '''
x = per(c, '2025-02-01', '2025-02-28')
m = x['nm'].str.contains('trà sữa ô long|tra sua o long') & x['nm'].str.contains(r'\\(m\\)|\\bm\\b')
RESULT = int(to_num(x.loc[m, 'Số lượng']).sum())
''',

    # 23: (biz_106) từ đầu năm đến hết hnay cửa hàng bán được nhiêu tiền (as_of: 2026-02-17)
    'q_20ad1fe3cbcd': HEADER_106 + '''
x = per(c, '2026-01-01', as_of_date)
RESULT = int(x.v.sum())
''',

    # 24: (biz_106) Tính đến hết ngày 05/04/2025, tổng số tiền khách còn nợ ở các đơn đã đặt quá 7 ngày là bao nhiêu? (as_of: 2025-04-05)
    'q_23cea7790c35': HEADER_106 + '''
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
'''
}

correct_count = 0
for qid, code_str in solutions.items():
    code_path = f"/tmp/s9_001/{qid}.py"
    Path(code_path).write_text(code_str)
    cmd = [".venv/bin/python", "code/haiku_check.py", "batches_retry9/retry9_001.jsonl", qid, code_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    out = res.stdout.strip()
    status = "CORRECT" if "CORRECT" in out else "WRONG"
    if status == "CORRECT":
        correct_count += 1
    print(f"[{qid}] {status}: {out}")

print(f"\nBATCH 001 FINISHED: {correct_count}/25 correct!")
