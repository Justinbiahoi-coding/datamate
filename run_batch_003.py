import json, subprocess, os, sys
from pathlib import Path

Path('/tmp/s9_003').mkdir(parents=True, exist_ok=True)

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
h_clean = h[~h['Trạng thái'].str.contains('hủy|huỷ|trả|hoàn trả', case=False, na=False)].copy()

c = pd.concat([DanhSachHoaDonChiTiet_1, DanhSachHoaDonChiTiet_2], ignore_index=True).drop_duplicates(['Mã hóa đơn','STT'])
c['v'] = c['Thành tiền'].map(money)
c['cost'] = c['Giá vốn'].map(money)
c['sl'] = to_num(c['Số lượng'])
c['sl_qd'] = to_num(c['Số lượng quy đổi'])

c = c.merge(h_clean[['Mã hóa đơn','dt']], on='Mã hóa đơn')
c['nm'] = c['Tên hàng'].map(lambda s: re.sub(r'\\s+',' ',unicodedata.normalize('NFC',str(s))).strip().casefold())
def per(df,a,b): return df[(df['dt']>=a)&(df['dt']<=b)]
def rd(x): return int(math.floor(x+0.5))
'''

HEADER_107 = '''import unicodedata, re, math
df = SoBanHang.copy()
df['dt'] = parse_date(df.ngay_ban)
st = df['Trạng thái xử lý'].astype(str).str.lower()
df = df[~st.str.contains('hủy|huỷ|cancel|trả|không giao được')].copy()
df['tot'] = to_num(df['Tổng tiền'])
df['sl'] = to_num(df['Số lượng'])
df['sl_le'] = to_num(df['Số lượng lẻ'])
df['nm'] = df['Nội dung'].map(lambda s: re.sub(r'\\s+',' ',unicodedata.normalize('NFC',str(s))).strip().casefold())
def per(d,a,b): return d[(d['dt']>=a)&(d['dt']<=b)]
'''

solutions = {
    # 00: (biz_106) Có bao nhiêu khách đang còn thiếu tiền cửa hàng tính tới hết ngày 12/04/2025 nhỉ? (as_of: 2025-04-12)
    'q_cc989ac5d7a0': HEADER_106 + '''
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
g = h_debt[h_debt['owe'] > 0].groupby('Mã KH')['owe'].sum()
RESULT = int((g > 0).sum())
''',

    # 01: (biz_106) cho hỏi số đơn 7 ngày gaanf nhất là bnhiu hả (as_of: 2026-07-12)
    'q_d53bf9328c13': HEADER_106 + '''
start_date = (pd.to_datetime(as_of_date) - pd.Timedelta(days=6)).strftime('%Y-%m-%d')
x = per(c, start_date, as_of_date)
RESULT = int(x['Mã hóa đơn'].nunique())
''',

    # 02: (biz_106) cho hoi trong thang nay, so ly size m ban duoc la bao nhieu, tinh moi loai do uong do (as_of: 2026-09-14)
    'q_dac20ca9084f': HEADER_106 + '''
x = per(c, '2026-09-01', as_of_date)
m = x['nm'].str.contains(r'\\(m\\)|\\bm\\b') & (x['Đơn vị tính'].str.lower() == 'ly')
RESULT = int(x.loc[m, 'sl'].sum())
''',

    # 03: (biz_106) Tháng 7/2026 cửa hàng bán được tổng cộng bao nhiêu tiền?
    'q_dedf1e05d641': HEADER_106 + '''
x = per(c, '2026-07-01', '2026-07-31')
RESULT = int(x.v.sum())
''',

    # 04: (biz_106) Tuần trước riêng ca sáng bán được tổng cộng bao nhiêu tiền? (as_of: 2026-07-28, Tue -> 2026-07-20..2026-07-26)
    'q_df06bb859b32': HEADER_106 + '''
x = per(c, '2026-07-20', '2026-07-26')
# ca sáng: 06:00 to 13:59
m = x['dt'].dt.hour.between(6, 13)
RESULT = int(x.loc[m, 'v'].sum())
''',

    # 05: (biz_106) Trong tháng này, tiền khách trả bớt nợ các đơn mua chịu đc bao nhiêu? (as_of: 2026-09-14)
    'q_df1caa0fd643': HEADER_106 + '''
h_debt = DanhSachHoaDon.drop_duplicates('Mã hóa đơn').copy()
h_debt['od'] = parse_date(h_debt['Thời gian']).dt.normalize()
debt = h_debt[(h_debt['Phương thức thanh toán'] == 'Ghi nợ') & (~h_debt['Trạng thái'].str.contains('hủy|huỷ', case=False, na=False))]

q = SoQuy.copy()
q['qd'] = parse_date(q['Thời gian']).dt.normalize()
q['v'] = q['Giá trị'].map(money)

m = q.merge(debt[['Mã hóa đơn', 'od']], on='Mã hóa đơn')
m_sep = m[(m.qd > m.od) & (m.qd >= '2026-09-01') & (m.qd <= as_of_date)]
RESULT = int(round(m_sep.v.sum()))
''',

    # 06: (biz_106) Xem giúp ngày 11/02/2026 cửa hàng bán Sinh tố xoài (M) giá bao nhiêu một ly?
    'q_e0eb2f43ba7b': HEADER_106 + '''
c['d'] = c['dt'].dt.normalize()
m = c['nm'].str.contains('sinh tố xoài') & c['nm'].str.contains(r'\\(m\\)|\\bm\\b') & (c['d'] == '2026-02-11')
RESULT = int(money(c.loc[m, 'Đơn giá'].iloc[0]))
''',

    # 07: (biz_106) Đếm số đơn hàng tháng 4/2025 có tiền hàng từ 55.000 đồng trở lên.
    'q_e95de19f41e5': HEADER_106 + '''
x = per(c, '2025-04-01', '2025-04-30')
g = x.groupby('Mã hóa đơn').v.sum()
RESULT = int((g >= 55000).sum())
''',

    # 08: (biz_106) tong tien hang nhap vao thang 3/2025 la bao nhieu ta
    'q_e9f855ca763f': HEADER_106 + '''
nh = DanhSachNhapHang.copy()
nh['d'] = parse_date(nh['Thời gian'])
nh = nh[~nh['Trạng thái'].astype(str).str.contains('hủy|huỷ', case=False, na=False)]
nh_mar = nh[(nh.d >= '2025-03-01') & (nh.d <= '2025-03-31')]
RESULT = int(round(nh_mar['Cần trả NCC'].map(money).sum()))
''',

    # 09: (biz_106) trong tháng 5/2025, tiền khách trả bớt nợ các đơn mua chịu được bao nhiêu
    'q_f24714cccf9d': HEADER_106 + '''
h_debt = DanhSachHoaDon.drop_duplicates('Mã hóa đơn').copy()
h_debt['od'] = parse_date(h_debt['Thời gian']).dt.normalize()
debt = h_debt[(h_debt['Phương thức thanh toán'] == 'Ghi nợ') & (~h_debt['Trạng thái'].str.contains('hủy|huỷ', case=False, na=False))]

q = SoQuy.copy()
q['qd'] = parse_date(q['Thời gian']).dt.normalize()
q['v'] = q['Giá trị'].map(money)

m = q.merge(debt[['Mã hóa đơn', 'od']], on='Mã hóa đơn')
m_may = m[(m.qd > m.od) & (m.qd >= '2025-05-01') & (m.qd <= '2025-05-31')]
RESULT = int(round(m_may.v.sum()))
''',

    # 10: (biz_106) cho hoi dthu cac don tra bang chuyen khoan thang nay la bao nhieu (as_of: 2026-09-14)
    'q_f30ba7c5b587': HEADER_106 + '''
h_ck = h_clean[h_clean['Phương thức thanh toán'].astype(str).str.contains('chuyển khoản', case=False)]
c_ck = c[c['Mã hóa đơn'].isin(h_ck['Mã hóa đơn'])]
x = per(c_ck, '2026-09-01', as_of_date)
RESULT = int(x.v.sum())
''',

    # 11: (biz_106) Cho hỏi tháng 8/2026 ca chiều bán được bao nhiêu tiền? (14:00 to 21:59)
    'q_f4a89e1d7ba0': HEADER_106 + '''
x = per(c, '2026-08-01', '2026-08-31')
m = x['dt'].dt.hour.between(14, 21)
RESULT = int(x.loc[m, 'v'].sum())
''',

    # 12: (biz_106) Tháng 3/2026 cửa hàng bán đc tổng cộng bao nhiêu cái Bánh tiramisu?
    'q_f76e9f531b6c': HEADER_106 + '''
x = per(c, '2026-03-01', '2026-03-31')
m = x['nm'].str.contains('tiramisu')
RESULT = int(x.loc[m, 'sl'].sum())
''',

    # 13: (biz_106) thang 2/2026 co bao nhieu mat hang xuat hien trong it nhat 107 don hang
    'q_f91bb056b0b6': HEADER_106 + '''
x = per(c, '2026-02-01', '2026-02-28')
g = x.groupby('Mã hàng')['Mã hóa đơn'].nunique()
RESULT = int((g >= 107).sum())
''',

    # 14: (biz_106) tong dthu thang 2 nam 2026 la bao nhieu do
    'q_fc7ccf7590eb': HEADER_106 + '''
x = per(c, '2026-02-01', '2026-02-28')
RESULT = int(x.v.sum())
''',

    # 15: (biz_107) Cho tôi biết doanh thu hôm qua. (as_of: 2026-04-18 -> 2026-04-17)
    'q_0fb7868ac463': HEADER_107 + '''
yesterday = (pd.to_datetime(as_of_date) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
x = per(df, yesterday, yesterday)
RESULT = int(x['tot'].sum())
''',

    # 16: (biz_107) Cho tôi biết doanh thu tháng 3/2025.
    'q_18833548c734': HEADER_107 + '''
x = per(df, '2025-03-01', '2025-03-31')
RESULT = int(x['tot'].sum())
''',

    # 17: (biz_107) gia ban mot goi keo alpenliebe 100g vao ngay 15/04/2025 la bn
    'q_22184c4bfb6b': HEADER_107 + '''
alp = df[df['nm'].str.contains('alpenliebe') & (df.dt <= '2025-04-15')].sort_values('dt')
RESULT = int(to_num(alp.iloc[-1]['don_gia']))
''',

    # 18: (biz_107) Tháng 1/2026 mặt hàng Nếp cái hoa vàng bán được tổng cộng bao nhiêu kg?
    'q_2d2b39ab0b27': HEADER_107 + '''
x = per(df, '2026-01-01', '2026-01-31')
m = x['nm'].str.contains('nếp cái hoa vàng')
RESULT = int(x.loc[m, 'sl_le'].sum())
''',

    # 19: (biz_107) Tổng doanh thu quý 1/2026 là bao nhiêu?
    'q_3f43a03d2d37': HEADER_107 + '''
x = per(df, '2026-01-01', '2026-03-31')
RESULT = int(x['tot'].sum())
''',

    # 20: (biz_107) xem giup hqua cua hang ban duoc bao nhiu tien (as_of: 2026-06-23 -> 2026-06-22)
    'q_43bd8e35df66': HEADER_107 + '''
yesterday = (pd.to_datetime(as_of_date) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
x = per(df, yesterday, yesterday)
RESULT = int(x['tot'].sum())
''',

    # 21: (biz_107) Doanh thu hôm qua của cửa hàng là bao nhiêu? (as_of: 2025-07-21 -> 2025-07-20)
    'q_4e10737a6074': HEADER_107 + '''
yesterday = (pd.to_datetime(as_of_date) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
x = per(df, yesterday, yesterday)
RESULT = int(x['tot'].sum())
''',

    # 22: (biz_107) trong thang 12 nam 2025 cua hang ban duoc may kg Nep cai hoa vang
    'q_5128ae09fefb': HEADER_107 + '''
x = per(df, '2025-12-01', '2025-12-31')
m = x['nm'].str.contains('nếp cái hoa vàng')
RESULT = int(x.loc[m, 'sl_le'].sum())
''',

    # 23: (biz_107) Hôm nay cửa hàng bán được bao nhiêu tiền? (as_of: 2026-05-16)
    'q_653d140d659c': HEADER_107 + '''
x = per(df, as_of_date, as_of_date)
RESULT = int(x['tot'].sum())
''',

    # 24: (biz_107) Quý 2 năm 2026 cửa hàng bán được tổng cộng bao nhiêu tiền? (2026-04-01..2026-06-30)
    'q_7940a4484419': HEADER_107 + '''
x = per(df, '2026-04-01', '2026-06-30')
RESULT = int(x['tot'].sum())
'''
}

correct_count = 0
for qid, code_str in solutions.items():
    code_path = f"/tmp/s9_003/{qid}.py"
    Path(code_path).write_text(code_str)
    cmd = [".venv/bin/python", "code/haiku_check.py", "batches_retry9/retry9_003.jsonl", qid, code_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    out = res.stdout.strip()
    status = "CORRECT" if "CORRECT" in out else "WRONG"
    if status == "CORRECT":
        correct_count += 1
    print(f"[{qid}] {status}: {out}")

print(f"\nBATCH 003 FINISHED: {correct_count}/25 correct!")
