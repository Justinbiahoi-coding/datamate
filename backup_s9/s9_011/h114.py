"""Helpers for biz_114 (flat CSV, one row per order line)."""
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
        b = load_business(ROOT / 'train' / 'data' / 'biz_114')
        df = b['ban_hang'].copy()
        df['dt'] = dates(df['Ngày'])
        st = df['trang_thai'].astype(str).str.strip()
        df['st_norm'] = np.select(
            [st.str.contains('huỷ|hủy|cancel', case=False, na=False),
             st.str.contains('trả|return', case=False, na=False)],
            ['cancel', 'return'], default='ok')
        df['rev'] = mnum(df['Tổng'])
        df['qty'] = pd.to_numeric(df['Quy ra ĐV lẻ'], errors='coerce')
        df['name_n'] = df['Sản phẩm'].map(norm)
        _b = df
    return _b


def day_mask(df, day):
    d = pd.Timestamp(day)
    return (df['dt'] >= d) & (df['dt'] < d + pd.Timedelta(days=1))


def month_mask(df, y, m):
    s = pd.Timestamp(year=y, month=m, day=1)
    e = s + pd.offsets.MonthBegin(1)
    return (df['st_norm'] == 'ok') & (df['dt'] >= s) & (df['dt'] < e)


def range_mask(df, start, end):
    s = pd.Timestamp(start)
    e = pd.Timestamp(end) + pd.Timedelta(days=1)
    return (df['st_norm'] == 'ok') & (df['dt'] >= s) & (df['dt'] < e)
