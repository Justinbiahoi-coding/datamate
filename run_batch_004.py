import json, subprocess, os, sys
from pathlib import Path

Path('/tmp/s9_004').mkdir(parents=True, exist_ok=True)

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
def rd(x): return int(math.floor(x+0.5))
'''

HEADER_108 = '''import unicodedata, re, math
h = DanhSachHoaDon.drop_duplicates('Mã hóa đơn').copy()
h['dt'] = parse_date(h['Thời gian'])
h['t_tao'] = parse_date(h['Thời gian tạo'])
h = h[~h['Trạng thái'].astype(str).str.contains('hủy|huỷ|trả', case=False, na=False)].copy()
h['tot'] = to_num(h['Tổng tiền hàng'])

c = DanhSachHoaDonChiTiet.drop_duplicates(['Mã hóa đơn', 'STT']).copy()
c['v'] = to_num(c['Thành tiền'])
c['sl'] = to_num(c['Số lượng'])
c['sl_qd'] = to_num(c['Số lượng quy đổi'])
c = c.merge(h[['Mã hóa đơn', 'dt', 't_tao', 'Kênh bán', 'Người bán']], on='Mã hóa đơn')
c['nm'] = c['Tên hàng'].map(lambda s: re.sub(r'\\s+',' ',unicodedata.normalize('NFC',str(s))).strip().casefold())
def per(df,a,b): return df[(df['dt']>=a)&(df['dt']<=b)]
def rd(x): return int(math.floor(x+0.5))
'''

solutions = {
    # 00: (biz_107) Doanh thu của Nước rửa chén Sunlight 750g trong tháng 7 năm 2025 là bao nhiêu?
    'q_9e21b57bd33c': HEADER_107 + '''
x = per(df, '2025-07-01', '2025-07-31')
m = x['nm'].str.contains('sunlight 750g')
RESULT = int(x.loc[m, 'tot'].sum())
''',

    # 01: (biz_107) tháng 2/2026 cửa hàng bán đươc total bao nhiu tiền
    'q_a2011de083ca': HEADER_107 + '''
x = per(df, '2026-02-01', '2026-02-28')
RESULT = int(x['tot'].sum())
''',

    # 02: (biz_107) Tổng doanh thu tháng 6 năm 2026 là bao nhiêu?
    'q_a28c02a0caa6': HEADER_107 + '''
x = per(df, '2026-06-01', '2026-06-30')
RESULT = int(x['tot'].sum())
''',

    # 03: (biz_107) hôm nay cuwar hangf bán đươc bao nhiu tiền z (as_of: 2025-12-28)
    'q_c1c2d4383a19': HEADER_107 + '''
x = per(df, as_of_date, as_of_date)
RESULT = int(x['tot'].sum())
''',

    # 04: (biz_107) cho hoi thang 3/2025 ban ra bao nhieu kg nep cai hoa vang
    'q_c999f3c68769': HEADER_107 + '''
x = per(df, '2025-03-01', '2025-03-31')
m = x['nm'].str.contains('nếp cái hoa vàng')
RESULT = int(x.loc[m, 'sl_le'].sum())
''',

    # 05: (biz_107) doanh thu cua Nuoc suoi Aquafina 500ml trong thang 4 nam 2025 la bnhiu z
    'q_dd2ac0bf2d64': HEADER_107 + '''
x = per(df, '2025-04-01', '2025-04-30')
m = x['nm'].str.contains('aquafina 500ml')
RESULT = int(x.loc[m, 'tot'].sum())
''',

    # 06: (biz_107) Doanh thu hôm qua của cửa hàng là bao nhiêu? (as_of: 2026-07-03 -> 2026-07-02)
    'q_df417afd658b': HEADER_107 + '''
yesterday = (pd.to_datetime(as_of_date) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
x = per(df, yesterday, yesterday)
RESULT = int(x['tot'].sum())
''',

    # 07: (biz_107) Trong tháng 6 năm 2025 cửa hàng bán được mấy kg Nếp cái hoa vàng?
    'q_e94f699997e5': HEADER_107 + '''
x = per(df, '2025-06-01', '2025-06-30')
m = x['nm'].str.contains('nếp cái hoa vàng')
RESULT = int(x.loc[m, 'sl_le'].sum())
''',

    # 08: (biz_107) Hôm qua cửa hàng bán được bao nhiêu tiền? (as_of: 2025-06-27 -> 2025-06-26)
    'q_edd6b74b7f30': HEADER_107 + '''
yesterday = (pd.to_datetime(as_of_date) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
x = per(df, yesterday, yesterday)
RESULT = int(x['tot'].sum())
''',

    # 09: (biz_108) gia ban mot goi mi hao hao tom chua cay vao ngay 21/04/2026 la bnhiu ta
    'q_058e9b27fb45': HEADER_108 + '''
m = c['nm'].str.contains('hảo hảo tôm chua cay') & (c.dt <= '2026-04-21')
sub = c[m].sort_values('dt')
RESULT = int(to_num(sub.iloc[-1]['Đơn giá']))
''',

    # 10: (biz_108) cho hoi dthu cua nhan vien ma NV001 thang 4/2025 la bao nhieu
    'q_16a0a8ef25c5': HEADER_108 + '''
x = per(h, '2025-04-01', '2025-04-30')
m = x['Người bán'] == 'NV001'
RESULT = int(x.loc[m, 'tot'].sum())
''',

    # 11: (biz_108) Cho tôi biết doanh thu hqua (as_of: 2025-06-28 -> 2025-06-27)
    'q_1b1166dfb4dd': HEADER_108 + '''
yesterday = (pd.to_datetime(as_of_date) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
x = per(h, yesterday, yesterday)
RESULT = int(x['tot'].sum())
''',

    # 12: (biz_108) Giá nhập bình quân một thùng Bột giặt OMO 3kg trong tháng 6 năm 2025 là bao nhiêu ạ?
    'q_1b4c510fa9d8': HEADER_108 + '''
nh = DanhSachNhapHang.copy()
nh['d'] = parse_date(nh['Thời gian'])
nh = nh[~nh['Trạng thái'].astype(str).str.contains('hủy|huỷ', case=False, na=False)]
nh_june = nh[(nh.d >= '2025-06-01') & (nh.d <= '2025-06-30')]
ct = DanhSachChiTietNhapHang[DanhSachChiTietNhapHang['Mã nhập hàng'].isin(nh_june['Mã nhập hàng'])].copy()
ct = ct.merge(DanhSachSanPham[['Mã hàng', 'Tên hàng']], on='Mã hàng')
m = ct['Tên hàng'].str.lower().str.contains('omo') & (ct['ĐVT'].str.lower() == 'thùng')
sub = ct[m].copy()
sub['sl'] = to_num(sub['Số lượng'])
sub['dg'] = to_num(sub['Đơn giá'])
RESULT = rd((sub['sl'] * sub['dg']).sum() / sub['sl'].sum())
''',

    # 13: (biz_108) nhân viên mã NV003 tháng 12/2025 bán dc tổng cộng bao nhiu tiền nhỉ
    'q_1c39f9ff5e6a': HEADER_108 + '''
x = per(h, '2025-12-01', '2025-12-31')
m = x['Người bán'] == 'NV003'
RESULT = int(x.loc[m, 'tot'].sum())
''',

    # 14: (biz_108) dthu hôm nay là bao nhiêu? (as_of: 2025-06-23)
    'q_24c116dc02b2': HEADER_108 + '''
x = per(h, as_of_date, as_of_date)
RESULT = int(x['tot'].sum())
''',

    # 15: (biz_108) check gium doanh thu ca chieu tuan trc la bao nhiu (as_of: 2026-05-16, Sat -> 2026-05-04..2026-05-10)
    'q_27ea93d85fa6': HEADER_108 + '''
x = per(h, '2026-05-04', '2026-05-10')
m = x['t_tao'].dt.hour.between(14, 21)
RESULT = int(x.loc[m, 'tot'].sum())
''',

    # 16: (biz_108) Hôm nay cửa hàng có bao nhiêu đơn? (as_of: 2026-05-11)
    'q_4362460c082a': HEADER_108 + '''
x = per(h, as_of_date, as_of_date)
RESULT = int(x['Mã hóa đơn'].nunique())
''',

    # 17: (biz_108) tháng 3/2025 doanh thu các đơn bán tại quầy đươc nhiêu
    'q_63ebf4ee8900': HEADER_108 + '''
x = per(h, '2025-03-01', '2025-03-31')
m = x['Kênh bán'].str.lower().str.contains('tại quầy|tai quay')
RESULT = int(x.loc[m, 'tot'].sum())
''',

    # 18: (biz_108) cho hỏi hnay kho còn tồn bao nhiu gói đậu phộng rang muối 200g lúc cuối ngày
    'q_6b559052cde1': HEADER_108 + '''
tk = BaoCaoTonKho.copy()
m = tk['Tên hàng'].str.lower().str.contains('đậu phộng rang muối')
RESULT = int(to_num(tk.loc[m, 'Tồn cuối kỳ']).iloc[0])
''',

    # 19: (biz_108) Tháng 4/2026 nhân viên mã NV003 bán được bao nhiêu tiền?
    'q_708812ce5e79': HEADER_108 + '''
x = per(h, '2026-04-01', '2026-04-30')
m = x['Người bán'] == 'NV003'
RESULT = int(x.loc[m, 'tot'].sum())
''',

    # 20: (biz_108) thang 2/2026 tong gia tri cac phieu nhap hang la bn
    'q_73a245d4339b': HEADER_108 + '''
nh = DanhSachNhapHang.copy()
nh['d'] = parse_date(nh['Thời gian'])
nh = nh[~nh['Trạng thái'].astype(str).str.contains('hủy|huỷ', case=False, na=False)]
nh_feb = nh[(nh.d >= '2026-02-01') & (nh.d <= '2026-02-28')]
RESULT = int(round(to_num(nh_feb['Cần trả NCC']).sum()))
''',

    # 21: (biz_108) dthu trung bình treen một đơn tháng 7/2025 là bnhiu
    'q_73d796ecc405': HEADER_108 + '''
x = per(h, '2025-07-01', '2025-07-31')
RESULT = rd(x['tot'].mean())
''',

    # 22: (biz_108) check giùm toonf kho trà xanh 0 độ 455ml cuối ngày hôm nay là bao nhiêu chai
    'q_7804abc7e4f4': HEADER_108 + '''
tk = BaoCaoTonKho.copy()
m = tk['Tên hàng'].str.lower().str.contains('trà xanh 0 độ')
RESULT = int(to_num(tk.loc[m, 'Tồn cuối kỳ']).iloc[0])
''',

    # 23: (biz_108) tháng 10/2025 nhập hàng hết bn tiền hả
    'q_818a3493a7ad': HEADER_108 + '''
nh = DanhSachNhapHang.copy()
nh['d'] = parse_date(nh['Thời gian'])
nh = nh[~nh['Trạng thái'].astype(str).str.contains('hủy|huỷ', case=False, na=False)]
nh_oct = nh[(nh.d >= '2025-10-01') & (nh.d <= '2025-10-31')]
RESULT = int(round(to_num(nh_oct['Cần trả NCC']).sum()))
''',

    # 24: (biz_108) Doanh thu quý 3/2025 của cửa hàng là bao nhiêu? (2025-07-01..2025-09-30)
    'q_8a93514387d0': HEADER_108 + '''
x = per(h, '2025-07-01', '2025-09-30')
RESULT = int(x['tot'].sum())
'''
}

correct_count = 0
for qid, code_str in solutions.items():
    code_path = f"/tmp/s9_004/{qid}.py"
    Path(code_path).write_text(code_str)
    cmd = [".venv/bin/python", "code/haiku_check.py", "batches_retry9/retry9_004.jsonl", qid, code_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    out = res.stdout.strip()
    status = "CORRECT" if "CORRECT" in out else "WRONG"
    if status == "CORRECT":
        correct_count += 1
    print(f"[{qid}] {status}: {out}")

print(f"\nBATCH 004 FINISHED: {correct_count}/25 correct!")
