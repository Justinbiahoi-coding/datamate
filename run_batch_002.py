import json, subprocess, os, sys
from pathlib import Path

Path('/tmp/s9_002').mkdir(parents=True, exist_ok=True)

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

solutions = {
    # 00: Trong tháng 7/2026, bao nhiêu đơn có tiền hàng đạt 130.000 đồng trở lên nhỉ?
    'q_2a0e86444947': HEADER_106 + '''
x = per(c, '2026-07-01', '2026-07-31')
g = x.groupby('Mã hóa đơn').v.sum()
RESULT = int((g >= 130000).sum())
''',

    # 01: Tháng 10/2025 cửa hàng bán được tổng cộng bao nhiêu tiền vậy?
    'q_2bf6b2b1b7b7': HEADER_106 + '''
x = per(c, '2025-10-01', '2025-10-31')
RESULT = int(x.v.sum())
''',

    # 02: Tính đến hết ngày 16/12/2025, khách hàng còn nợ cửa hàng tổng cộng bao nhiêu tiền? (as_of: 2025-12-16)
    'q_32a692d7807b': HEADER_106 + '''
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

    # 03: dthu các đơn trả bằng chuyển khoản tháng 9/2025 là bao nhiêu?
    'q_37c963b963ef': HEADER_106 + '''
h_ck = h_clean[h_clean['Phương thức thanh toán'].astype(str).str.contains('chuyển khoản', case=False)]
c_ck = c[c['Mã hóa đơn'].isin(h_ck['Mã hóa đơn'])]
x = per(c_ck, '2025-09-01', '2025-09-30')
RESULT = int(x.v.sum())
''',

    # 04: thang 4/2025 quan ban ra tong cong may ly size l, cong tat ca cac mon
    'q_465a4bdab726': HEADER_106 + '''
x = per(c, '2025-04-01', '2025-04-30')
m = x['nm'].str.contains(r'\\(l\\)|\\bl\\b') & (x['Đơn vị tính'].str.lower() == 'ly')
RESULT = int(x.loc[m, 'sl'].sum())
''',

    # 05: tinh lai gop thang 12/2025
    'q_501e4b45bd00': HEADER_106 + '''
x = per(c, '2025-12-01', '2025-12-31')
RESULT = int(round(x['v'].sum() - (x['cost'] * x['sl']).sum()))
''',

    # 06: Đến hết ngày 11/04/2025, số tiền khách còn thiếu là bao nhiêu? (as_of: 2025-04-11)
    'q_59ababa26d62': HEADER_106 + '''
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

    # 07: thang 8/2025 quan ban ra tong cong may ly size m, cong tat ca cac mon
    'q_6142648cb6c8': HEADER_106 + '''
x = per(c, '2025-08-01', '2025-08-31')
m = x['nm'].str.contains(r'\\(m\\)|\\bm\\b') & (x['Đơn vị tính'].str.lower() == 'ly')
RESULT = int(x.loc[m, 'sl'].sum())
''',

    # 08: Doanh thu tháng 8/2026 so với tháng 8/2025 tăng hay giảm bao nhiêu %?
    'q_6d251adc4eab': HEADER_106 + '''
a25 = per(c, '2025-08-01', '2025-08-31').v.sum()
a26 = per(c, '2026-08-01', '2026-08-31').v.sum()
pct = round((a26 - a25) / a25 * 100, 2)
RESULT = f"{pct:.2f}%"
''',

    # 09: cho hoi thang 5/2026, dthu cac don tra bang chuyen khoan la bao nhieu
    'q_72d7deb192d7': HEADER_106 + '''
h_ck = h_clean[h_clean['Phương thức thanh toán'].astype(str).str.contains('chuyển khoản', case=False)]
c_ck = c[c['Mã hóa đơn'].isin(h_ck['Mã hóa đơn'])]
x = per(c_ck, '2026-05-01', '2026-05-31')
RESULT = int(x.v.sum())
''',

    # 10: Trung bình mỗi đơn tháng 2/2025 mang về bao nhiêu doanh thu?
    'q_7aa8bcb83116': HEADER_106 + '''
x = per(c, '2025-02-01', '2025-02-28')
RESULT = rd(x.groupby('Mã hóa đơn').v.sum().mean())
''',

    # 11: xem giúp cho tôi biết lời gộp tháng 9 nawm 2025
    'q_81cc91f86744': HEADER_106 + '''
x = per(c, '2025-09-01', '2025-09-30')
RESULT = int(round(x['v'].sum() - (x['cost'] * x['sl']).sum()))
''',

    # 12: Đến hết ngày 17/12/2025, số khách còn công nợ với cửa hàng là bao nhiêu? (as_of: 2025-12-17)
    'q_831658029945': HEADER_106 + '''
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

    # 13: Tháng 6/2026 nhóm bánh chiếm bao nhiêu % doanh thu?
    'q_83878331afed': HEADER_106 + '''
x = per(c, '2026-06-01', '2026-06-30').copy()
sp = DanhSachSanPham[['Mã hàng', 'Nhóm hàng(3 Cấp)']].copy()
x = x.merge(sp, on='Mã hàng', how='left')
cake_rev = x.loc[x['Nhóm hàng(3 Cấp)'].str.lower() == 'bánh', 'v'].sum()
tot_rev = x['v'].sum()
pct = round(cake_rev / tot_rev * 100, 2)
RESULT = f"{pct:.2f}%"
''',

    # 14: đến hết ngày 25/04/2026, các khoản nợ có tuổi quá 15 ngày còn bao nhiu tiền (as_of: 2026-04-25)
    'q_87fe5ac2d2b1': HEADER_106 + '''
h_debt = DanhSachHoaDon.drop_duplicates('Mã hóa đơn').copy()
h_debt = h_debt[~h_debt['Trạng thái'].astype(str).str.contains('hủy|huỷ|cancel', case=False, na=False)]
h_debt = h_debt[h_debt['Phương thức thanh toán'] != 'Thu hộ (COD)']
h_debt = h_debt[h_debt['Mã KH'].notna()]
h_debt['d'] = parse_date(h_debt['Thời gian'])
h_debt = h_debt[h_debt['d'] <= pd.Timestamp(as_of_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]
cutoff = pd.Timestamp(as_of_date) - pd.Timedelta(days=15)
h_debt = h_debt[h_debt['d'] < cutoff]
h_debt['tot'] = to_num(h_debt['Tổng sau giảm giá'])

sq = SoQuy.copy()
sq['v'] = sq['Giá trị'].map(money)
sq['t'] = parse_date(sq['Thời gian'])
sq = sq[sq['t'] <= pd.Timestamp(as_of_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]
paid = sq.groupby('Mã hóa đơn')['v'].sum()
h_debt['owe'] = h_debt['tot'] - h_debt['Mã hóa đơn'].map(paid).fillna(0)
RESULT = int(round(h_debt.loc[h_debt['owe'] > 0, 'owe'].sum()))
''',

    # 15: tháng 4/2026 nhaapj hàng hết bnhiu tieenf
    'q_8bcc01e76de8': HEADER_106 + '''
nh = DanhSachNhapHang.copy()
nh['d'] = parse_date(nh['Thời gian'])
nh = nh[~nh['Trạng thái'].astype(str).str.contains('hủy|huỷ', case=False, na=False)]
nh_apr = nh[(nh.d >= '2026-04-01') & (nh.d <= '2026-04-30')]
RESULT = int(round(nh_apr['Cần trả NCC'].map(money).sum()))
''',

    # 16: Tính đến hết ngày 23/03/2026, khách còn nợ cửa hàng tổng cộng bao nhiêu tiền? (as_of: 2026-03-23)
    'q_8ff6713cd1b9': HEADER_106 + '''
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

    # 17: check gium cong moi mon tinh theo ly, tuan trc ban ra dc may ly ha (as_of: 2025-12-18, Thu -> 2025-12-08..2025-12-14)
    'q_9587f9b496c8': HEADER_106 + '''
x = per(c, '2025-12-08', '2025-12-14')
m = x['Đơn vị tính'].str.lower() == 'ly'
RESULT = int(x.loc[m, 'sl'].sum())
''',

    # 18: dthu trung binh tren mot don tuan roi la bao nhieu (as_of: 2026-02-10, Tue -> 2026-02-02..2026-02-08)
    'q_969efac2de59': HEADER_106 + '''
x = per(c, '2026-02-02', '2026-02-08')
RESULT = rd(x.groupby('Mã hóa đơn').v.sum().mean())
''',

    # 19: xem giúp cửa hàng bán đươc bao nhiêu đơn trong quý 3 năm 2025 (2025-07-01..2025-09-30)
    'q_a54cc8dccf38': HEADER_106 + '''
x = per(c, '2025-07-01', '2025-09-30')
RESULT = int(x['Mã hóa đơn'].nunique())
''',

    # 20: Đếm số mặt hàng có mặt ở ≥ 92 đơn hàng khác nhau trong tháng 2/2025.
    'q_a965ab7a53ee': HEADER_106 + '''
x = per(c, '2025-02-01', '2025-02-28')
g = x.groupby('Mã hàng')['Mã hóa đơn'].nunique()
RESULT = int((g >= 92).sum())
''',

    # 21: tháng 2/2025 quán bán đc bao nhiu ly size l
    'q_b5c0715af111': HEADER_106 + '''
x = per(c, '2025-02-01', '2025-02-28')
m = x['nm'].str.contains(r'\\(l\\)|\\bl\\b') & (x['Đơn vị tính'].str.lower() == 'ly')
RESULT = int(x.loc[m, 'sl'].sum())
''',

    # 22: trong tháng 11/2025, bao nhiêu sp có mặt trong ít nhất 145 bill
    'q_bfa382e47ca0': HEADER_106 + '''
x = per(c, '2025-11-01', '2025-11-30')
g = x.groupby('Mã hàng')['Mã hóa đơn'].nunique()
RESULT = int((g >= 145).sum())
''',

    # 23: trong quý 3 năm 2025, dthu của cửa hàng được bao nhiêu tiền (2025-07-01..2025-09-30)
    'q_c35d62abb7b7': HEADER_106 + '''
x = per(c, '2025-07-01', '2025-09-30')
RESULT = int(x.v.sum())
''',

    # 24: Cho mình biết doanh thu tuần này. (as_of: 2025-12-06, Sat -> 2025-12-01..2025-12-06)
    'q_cadff21c3eac': HEADER_106 + '''
x = per(c, '2025-12-01', '2025-12-06')
RESULT = int(x.v.sum())
'''
}

correct_count = 0
for qid, code_str in solutions.items():
    code_path = f"/tmp/s9_002/{qid}.py"
    Path(code_path).write_text(code_str)
    cmd = [".venv/bin/python", "code/haiku_check.py", "batches_retry9/retry9_002.jsonl", qid, code_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    out = res.stdout.strip()
    status = "CORRECT" if "CORRECT" in out else "WRONG"
    if status == "CORRECT":
        correct_count += 1
    print(f"[{qid}] {status}: {out}")

print(f"\nBATCH 002 FINISHED: {correct_count}/25 correct!")
