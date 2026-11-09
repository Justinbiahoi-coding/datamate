"""Helpers for biz_116 (single Excel with sales/debt/delivery sheets)."""
import re, unicodedata, sys
from pathlib import Path
import pandas as pd, numpy as np

ROOT = Path('/Users/buivanthien/Learn/zalo chelen/datamate')
sys.path.insert(0, str(ROOT / 'code'))
from loader import load_business


def norm(s):
    s = str(s).lower().replace('đ', 'd')
    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', s).strip()


def money(s):
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
    s = s.replace(',', '')
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
                              'day': day.astype(int)}), errors='coerce')
        out.loc[rest] = parsed
    return out


_b = None


def tables():
    global _b
    if _b is None:
        b = load_business(ROOT / 'train' / 'data' / 'biz_116')
        B = b['Bao_cao_ban_hang']
        ct = B['So_chi_tiet_ban_hang'].copy()
        sp = B['Danh sách hàng hóa'].copy()

        ct['dt'] = dates(ct['Ngày'])
        st = ct['Trạng thái'].astype(str).str.strip()
        # two vocabularies: ok / khách hủy / trả hàng (<=2026-02)
        # and Thành công / Không giao được / Đã trả hàng / Đang vận chuyển (>=2026-03)
        ct['st_norm'] = np.select(
            [st.str.contains('hủy|huỷ|không giao', case=False, na=False),
             st.str.contains('trả', case=False, na=False)],
            ['cancel', 'return'], default='ok')
        ct['ttien'] = mnum(ct['Thành tiền'])
        ct['gia'] = mnum(ct['Đơn giá'])
        ct['slqd'] = pd.to_numeric(ct['Số lượng quy đổi'], errors='coerce')
        ct['name_n'] = ct['Tên hàng hóa'].map(norm)

        sp['name_n'] = sp['Tên hàng hóa'].map(norm)
        sp['group_n'] = sp['Nhóm hàng hóa'].map(norm)
        cmap = sp.drop_duplicates('name_n').set_index('name_n')
        ct['group_n'] = ct['name_n'].map(cmap['group_n'])
        _b = dict(ct=ct, sp=sp)
    return _b


def month_mask(dt, y, m):
    s = pd.Timestamp(year=y, month=m, day=1)
    e = s + pd.offsets.MonthBegin(1)
    return (dt >= s) & (dt < e)


def revenue(lines):
    return float(lines['ttien'].sum())


def avg_order(lines):
    rev = revenue(lines)
    n = lines['Mã đơn hàng'].nunique()
    return rev / n if n else 0.0


def group_rev(ct, y, m, group):
    sub = ct[(ct['st_norm'] == 'ok') & month_mask(ct['dt'], y, m)]
    return float(sub.loc[sub['group_n'] == norm(group), 'ttien'].sum())


def product_rev(ct, y, m, name):
    sub = ct[(ct['st_norm'] == 'ok') & month_mask(ct['dt'], y, m)]
    return float(sub.loc[sub['name_n'] == norm(name), 'ttien'].sum())


def product_qty(ct, start, end, name):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    sub = ct[(ct['st_norm'] == 'ok') & (ct['dt'] >= s) & (ct['dt'] < e)]
    return float(sub.loc[sub['name_n'] == norm(name), 'slqd'].sum())


def stale_items(ct, start, end):
    """Products sold before start but not sold in [start, end]."""
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    valid = ct[ct['st_norm'] == 'ok']
    before = set(valid.loc[valid['dt'] < s, 'name_n'])
    during = set(valid.loc[(valid['dt'] >= s) & (valid['dt'] < e), 'name_n'])
    return len(before - during)
