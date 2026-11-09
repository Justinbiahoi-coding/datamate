"""Shared helpers for batch retry9_007 (biz_109, biz_110, biz_111)."""
import re, unicodedata, sys
from pathlib import Path
import pandas as pd, numpy as np

ROOT = Path('/Users/buivanthien/Learn/zalo chelen/datamate')
sys.path.insert(0, str(ROOT / 'code'))
sys.path.insert(0, '/tmp/s9_006')
from loader import load_business



def norm(s):
    s = unicodedata.normalize('NFD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', s).strip()


def money(s):
    """Parse Vietnamese money strings ('240,000', '45k', '1,45tr')."""
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
        s = s.replace(',', '') if s.count(',') else s
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
    """Parse dates incl. Vietnamese '1 thg 1 2025', dd/mm/yyyy, ISO, Excel serial."""
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
        t = t.str.replace(r'\s*thg\s*', '/', regex=True)
        t = t.str.replace(r'\s*tháng\s*', '/', regex=True)
        t = t.str.replace(r'\s*-\s*', '-', regex=True)
        parts = t.str.extract(r'^(\d{1,4})[-/](\d{1,2})[-/](\d{1,4})')
        parsed = pd.Series(pd.NaT, index=t.index, dtype='datetime64[ns]')
        okp = parts.notna().all(axis=1)
        if okp.any():
            a, bb, c = parts.loc[okp, 0], parts.loc[okp, 1], parts.loc[okp, 2]
            year = c.where(c.str.len() == 4, a)
            month = bb
            day = a.where(c.str.len() == 4, c)
            parsed.loc[okp] = pd.to_datetime(
                pd.DataFrame({'year': year.astype(int), 'month': month.astype(int),
                              'day': day.astype(int)}),
                errors='coerce')
        if (~okp).any():
            parsed.loc[~okp] = pd.to_datetime(t.loc[~okp], errors='coerce', dayfirst=True)
        out.loc[rest] = parsed
    return out


_biz = {}


def biz(biz_id):
    if biz_id not in _biz:
        _biz[biz_id] = load_business(ROOT / 'train' / 'data' / biz_id)
    return _biz[biz_id]


# ── biz_109 (grocery) ───────────────────────────────────────────────────────
def t109():
    import importlib.util
    spec = importlib.util.spec_from_file_location('h109mod', '/tmp/s9_006/h.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.tables()


# ── biz_110 (single CSV invoices) ───────────────────────────────────────────
def t110():
    b = biz('biz_110')
    df = b['danh_sach_hoa_don'].copy()
    df = df[df['Mã bill'].notna()].copy()  # drop 'Cộng ngày' summary rows
    df['dt'] = dates(df['Ngày giao dịch'])
    df['rev'] = mnum(df['Tien hang'])
    st = df['Status'].astype(str).str.strip()
    df['st_norm'] = np.select(
        [st.str.contains('hủy|huỷ|cancel', case=False, na=False),
         st.str.contains('trả|return', case=False, na=False)],
        ['cancel', 'return'], default='ok')
    return dict(hd=df)


# ── biz_111 (coffee shop) ───────────────────────────────────────────────────
def t111():
    b = biz('biz_111')
    don = b['don_hang'].copy()
    ct = b['chi_tiet_don'].copy()
    sp = b['san_pham'].copy()
    kh = b['khach_hang'].copy()
    tt = b['thanh_toan'].copy()

    don['dt'] = dates(don['NgayBan'])
    st = don['Xử lý'].astype(str).str.strip()
    don['st_norm'] = np.select(
        [st.str.contains('cancelled|cancel|huỷ|hủy', case=False, na=False),
         st.str.contains('returned|return|trả', case=False, na=False)],
        ['cancel', 'return'], default='ok')
    don['bill'] = mnum(don['Tổng bill'])
    don['conlai'] = mnum(don['Còn lại'])

    ct['ttien'] = mnum(ct['T.Tiền'])
    ct['slqd'] = pd.to_numeric(ct['SL quy đổi'], errors='coerce')
    ct['gia'] = mnum(ct['Giá đơn vị'])
    sp['name_n'] = sp['Sản phẩm'].map(norm)
    sp['size'] = sp['Sản phẩm'].str.extract(r'\(([ML])\)$', flags=re.I)[0].str.upper()

    tt['dt'] = dates(tt['Thời gian thu'])
    tt['tien'] = mnum(tt['Tiền'])
    return dict(don=don, ct=ct, sp=sp, kh=kh, tt=tt)


def month_mask(dt_series, y, m):
    s = pd.Timestamp(year=y, month=m, day=1)
    e = s + pd.offsets.MonthBegin(1)
    return (dt_series >= s) & (dt_series < e)
