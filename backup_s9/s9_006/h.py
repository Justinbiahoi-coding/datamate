"""Shared helpers for biz_109 batch retry9_006."""
import re, unicodedata, sys
from pathlib import Path
import pandas as pd, numpy as np

ROOT = Path('/Users/buivanthien/Learn/zalo chelen/datamate')
sys.path.insert(0, str(ROOT / 'code'))
from loader import load_business

BIZ = 'biz_109'


def norm(s):
    s = unicodedata.normalize('NFD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', s).strip()


def money(s):
    """Parse Vietnamese money values. Handles '240,000', '45k', '1tr440', '1,45tr', 240000."""
    if isinstance(s, (int, float, np.integer, np.floating)) and not isinstance(s, bool):
        return float(s)
    s = str(s).strip().lower().replace('đ', '').replace('₫', '')
    if not s or s in ('nan', 'none'):
        return np.nan
    s = s.replace(' ', '')
    mult = 1.0
    if 'tr' in s:
        mult = 1_000_000.0
        s = s.replace('tr', '')
        # '1,45tr' -> 1.45
        if ',' in s and '.' not in s:
            s = s.replace(',', '.')
        s = s.replace(',', '')
    elif s.endswith('k'):
        mult = 1_000.0
        s = s[:-1]
        if ',' in s and '.' not in s:
            s = s.replace(',', '.')
        s = s.replace(',', '')
    else:
        s = s.replace(',', '').replace('.', '') if s.count('.') > 0 and s.count(',') > 0 else s.replace(',', '')
    s = re.sub(r'[^0-9.\-]', '', s)
    if s in ('', '-', '.'):
        return np.nan
    try:
        return float(s) * mult
    except Exception:
        return np.nan


def mnum(col):
    return pd.Series(col).map(money)


def dates(col):
    s = pd.Series(col)
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    out = pd.Series(pd.NaT, index=s.index, dtype='datetime64[ns]')
    num = pd.to_numeric(s, errors='coerce')
    mask = num.notna() & (num > 1000) & (num < 100000)
    if mask.any():
        out.loc[mask] = pd.Timestamp('1899-12-30') + pd.to_timedelta(num.loc[mask], unit='D')
    rest = s.notna() & ~mask
    if rest.any():
        t = s.loc[rest].astype(str).str.strip()
        iso = t.str.match(r'^\d{4}-\d{1,2}-\d{1,2}', na=False)
        parsed = pd.Series(pd.NaT, index=t.index, dtype='datetime64[ns]')
        if iso.any():
            parsed.loc[iso] = pd.to_datetime(t.loc[iso], errors='coerce')
        other = ~iso
        if other.any():
            parsed.loc[other] = pd.to_datetime(t.loc[other], errors='coerce', dayfirst=True)
        out.loc[rest] = parsed
    return out


_b = None


def biz():
    global _b
    if _b is None:
        _b = load_business(ROOT / 'train' / 'data' / BIZ)
    return _b


def tables():
    b = biz()
    D = b['DuLieuBanHang']
    hd = D['DanhSachHoaDon'].copy()
    ct = b['DanhSachHoaDonChiTiet'].copy()
    sp = D['DanhSachSanPham'].copy()
    dv = D['DanhSachDonViTinh'].copy()
    kh = D['DanhSachKhachHang'].copy()
    nhap = D['DanhSachNhapHang'].copy()
    ctn = D['DanhSachChiTietNhapHang'].copy()
    ton = D['BaoCaoTonKho'].copy()
    quy = D['SoQuy'].copy()

    hd['dt'] = dates(hd['Thời gian'])
    hd['dtt'] = dates(hd['Thời gian tạo'])
    st = hd['Trạng thái'].astype(str).str.strip()
    hd['st_norm'] = np.select(
        [st.str.contains('huỷ|hủy|cancel', case=False, na=False),
         st.str.contains('trả', case=False, na=False)],
        ['cancel', 'return'], default='ok')
    # 'Đang xử lý' / 'đã lấy' / 'Hoàn thành' are all kept (đang giao still counts)

    for c in ['Tổng tiền hàng', 'Giảm giá', 'Tổng sau giảm giá', 'Khách đã trả']:
        if c in hd:
            hd[c + '_n'] = mnum(hd[c])

    for c in ['Đơn giá', 'Giảm giá', 'Thành tiền', 'Giá vốn']:
        ct[c + '_n'] = mnum(ct[c])
    ct['sl'] = pd.to_numeric(ct['Số lượng'], errors='coerce')
    ct['slqd'] = pd.to_numeric(ct['Số lượng quy đổi'], errors='coerce')

    dv['qdoi'] = pd.to_numeric(dv['Quy đổi'], errors='coerce')
    # base unit = row with qdoi == 1
    base = dv[dv['qdoi'] == 1][['Mã hàng', 'ĐVT']].drop_duplicates('Mã hàng')
    base.columns = ['Mã hàng', 'base_unit']
    sp = sp.merge(base, on='Mã hàng', how='left')
    sp['name_n'] = sp['Tên hàng'].map(norm)

    nhap['dt'] = dates(nhap['Thời gian'])
    nhap['Cần trả NCC_n'] = mnum(nhap['Cần trả NCC'])
    ctn['sl'] = pd.to_numeric(ctn['Số lượng'], errors='coerce')
    ctn['Đơn giá_n'] = mnum(ctn['Đơn giá'])
    ton['Tồn cuối kỳ_n'] = pd.to_numeric(ton['Tồn cuối kỳ'], errors='coerce')

    quy['dt'] = dates(quy['Thời gian'])
    quy['Giá trị_n'] = mnum(quy['Giá trị'])

    return dict(hd=hd, ct=ct, sp=sp, dv=dv, kh=kh, nhap=nhap, ctn=ctn, ton=ton, quy=quy)


def valid_orders(t):
    hd = t['hd']
    return hd[hd['st_norm'] == 'ok']


def month_range(y, m):
    start = pd.Timestamp(year=y, month=m, day=1)
    end = start + pd.offsets.MonthBegin(1)
    return start, end


def revenue(t, mask_orders):
    """Revenue = sum of line Thành tiền of orders in mask_orders (index by order id)."""
    hd = t['hd']
    ids = set(hd.loc[mask_orders, 'Mã hóa đơn'])
    ct = t['ct']
    return float(ct.loc[ct['Mã hóa đơn'].isin(ids), 'Thành tiền_n'].sum())


def lines_of_valid(t, extra_mask=None):
    hd = t['hd']
    v = hd[hd['st_norm'] == 'ok'][['Mã hóa đơn', 'dt']]
    ct = t['ct'].merge(v, on='Mã hóa đơn', how='inner')
    if extra_mask is not None:
        ct = ct[extra_mask(ct)]
    return ct


def cost(t, mask_lines):
    return float((mask_lines['sl'] * mask_lines['Giá vốn_n']).sum())


def weekday_of(d):
    return pd.Timestamp(d).dayofweek  # Mon=0


def last_week(as_of):
    d = pd.Timestamp(as_of)
    monday_this = d - pd.Timedelta(days=d.dayofweek)
    start = monday_this - pd.Timedelta(days=7)
    end = monday_this  # exclusive
    return start, end
