"""Helpers for biz_117 (hand-written sales book + purchases + delivery)."""
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
    if 'tr' in s:
        left, right = s.split('tr', 1)
        try:
            base = float(left.replace(',', '.')) if left else 0.0
        except Exception:
            return np.nan
        extra = 0.0
        if right:
            try:
                extra = float(right) * 1000.0
            except Exception:
                extra = 0.0
        return base * 1_000_000.0 + extra
    if s.endswith('k'):
        try:
            return float(s[:-1].replace(',', '.')) * 1000.0
        except Exception:
            return np.nan
    s = re.sub(r'[^0-9.\-]', '', s.replace(',', ''))
    if s in ('', '-', '.'):
        return np.nan
    try:
        return float(s.replace('.', ''))
    except Exception:
        return np.nan


def qty_num(s):
    if isinstance(s, (int, float, np.integer, np.floating)) and not isinstance(s, bool):
        return float(s)
    m = re.search(r'-?\d+(?:[.,]\d+)?', str(s))
    if not m:
        return np.nan
    v = m.group().replace(',', '.')
    try:
        return float(v)
    except Exception:
        return np.nan


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
        t = t.str.replace(r'\s*thg\s*', '/', regex=True)
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
        if (~okp).any():
            parsed.loc[~okp] = pd.to_datetime(t.loc[~okp], errors='coerce', dayfirst=True)
        out.loc[rest] = parsed
    return out


_b = None


def tables():
    global _b
    if _b is None:
        b = load_business(ROOT / 'train' / 'data' / 'biz_117')

        # ── sales ────────────────────────────────────────────────────────
        ct = b['SoBanHang__all'].copy()
        ct = ct[ct['Mã phiếu'].notna()].copy()          # drop 'Tổng tháng' footer rows
        # exact repeated lines are data-entry duplication, count each sale once
        ct = ct.drop_duplicates(subset=['Giờ', 'Mã phiếu', 'TenKH', 'Ngày lập', 'Tiền',
                                        'Ghi chú TT', 'Giá', 'DonVi', 'Số lượng hàng', 'Tên SP']).copy()
        ct['dt'] = pd.to_datetime(ct['Giờ'], errors='coerce')
        st = ct['Ghi chú TT'].astype(str).str.strip()
        ct['st_norm'] = np.select(
            [st.str.contains('hủy|huỷ|cancel', case=False, na=False),
             st.str.contains('trả', case=False, na=False)],
            ['cancel', 'return'], default='ok')
        ct['ttien'] = ct['Tiền'].map(money)
        ct['gia'] = ct['Giá'].map(money)
        ct['qty'] = ct['Số lượng hàng'].map(qty_num)
        ct['name_n'] = ct['Tên SP'].map(norm)

        dm = b['DanhMuc'].copy()
        dm['Hệ số QĐ'] = pd.to_numeric(dm['Hệ số QĐ'], errors='coerce')
        dm['name_n'] = dm['Hàng'].map(norm)
        big = dm.drop_duplicates('name_n').set_index('name_n')
        ct['big_unit'] = ct['name_n'].map(big['ĐV lớn'])
        ct['factor'] = ct['name_n'].map(big['Hệ số QĐ'])
        is_big = ct['DonVi'].astype(str).str.strip() == ct['big_unit'].astype(str)
        ct['base_qty'] = np.where(is_big, ct['qty'] * ct['factor'].fillna(1.0), ct['qty'])
        ct['base_unit'] = np.where(is_big, ct['name_n'].map(big['ĐV nhỏ']), ct['DonVi'])

        # order-level validity: drop cancel orders and any order containing a return line
        negorders = set(ct.loc[ct['qty'] < 0, 'Mã phiếu'])
        cancel_orders = set(ct.loc[ct['st_norm'] == 'cancel', 'Mã phiếu'])
        return_orders = set(ct.loc[ct['st_norm'] == 'return', 'Mã phiếu']) | negorders
        ct['order_valid'] = ~ct['Mã phiếu'].isin(cancel_orders | return_orders)

        # ── delivery ─────────────────────────────────────────────────────
        gh = b['SoGiaoHang'].copy()
        gh['dt'] = dates(gh['Ngày chở'])

        # ── purchases ────────────────────────────────────────────────────
        nh = b['SoNhapHang'].copy()
        nh['dt'] = dates(nh['Ngày nhập'])
        nh['sl'] = nh['SL nhập'].map(qty_num)
        nh['gia'] = nh['Giá nhập'].map(money)
        nh['ttien'] = nh['Thành tiền'].map(money)
        nh['name_n'] = nh['Product'].map(norm)
        nh['big_unit'] = nh['name_n'].map(big['ĐV lớn'])
        nh['factor'] = nh['name_n'].map(big['Hệ số QĐ'])
        is_big_n = nh['ĐVT'].astype(str).str.strip() == nh['big_unit'].astype(str)
        nh['base_qty'] = np.where(is_big_n, nh['sl'] * nh['factor'].fillna(1.0), nh['sl'])

        ton = b['TonKho'].copy()
        ton['name_n'] = ton['Product'].map(norm)
        ton['ton'] = pd.to_numeric(ton['Tồn thực'], errors='coerce')

        bang = b['BangGia'].copy()
        bang['dt'] = dates(bang['Ngày áp dụng'])
        bang['gia_moi'] = bang['Giá mới'].map(money)
        bang['name_n'] = bang['TenHang'].map(norm)

        _b = dict(ct=ct, gh=gh, nh=nh, ton=ton, bang=bang, dm=dm)
    return _b


def month_mask(dt, y, m):
    s = pd.Timestamp(year=y, month=m, day=1)
    e = s + pd.offsets.MonthBegin(1)
    return (dt >= s) & (dt < e)


def orders_in(ct, start, end):
    """Distinct valid orders whose date lies in [start, end]."""
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    sub = ct[ct['order_valid'] & (ct['dt'] >= s) & (ct['dt'] < e)]
    return sub


def order_rev(ct, start, end):
    sub = orders_in(ct, start, end)
    return sub.groupby('Mã phiếu')['ttien'].sum()


def revenue(ct, start, end):
    return float(order_rev(ct, start, end).sum())


def n_orders(ct, start, end):
    return int(order_rev(ct, start, end).size)


def avg_order(ct, start, end):
    r = order_rev(ct, start, end)
    return float(r.sum()) / r.size if r.size else 0.0


def product_rev(ct, start, end, name):
    sub = ct[ct['order_valid'] & (ct['dt'] >= pd.Timestamp(start)) &
             (ct['dt'] < pd.Timestamp(end) + pd.Timedelta(days=1))]
    return float(sub.loc[sub['name_n'] == norm(name), 'ttien'].sum())


def product_qty(ct, start, end, name):
    sub = ct[ct['order_valid'] & (ct['dt'] >= pd.Timestamp(start)) &
             (ct['dt'] < pd.Timestamp(end) + pd.Timedelta(days=1))]
    return float(sub.loc[sub['name_n'] == norm(name), 'base_qty'].sum())


def stale_items(ct, start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    valid = ct[ct['order_valid']]
    before = set(valid.loc[valid['dt'] < s, 'name_n'])
    during = set(valid.loc[(valid['dt'] >= s) & (valid['dt'] < e), 'name_n'])
    return len(before - during)


def delivery_trips(gh, start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    sub = gh[(gh['dt'] >= s) & (gh['dt'] < e)]
    return int(sub[['Mã bill', 'Lượt giao']].drop_duplicates().shape[0])


def purchase_cost(nh, start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    sub = nh[(nh['dt'] >= s) & (nh['dt'] < e)]
    return float(sub['ttien'].sum())


def purchase_avg(nh, start, end, name, per_unit=None):
    """Weighted average purchase price over a period.

    per_unit: express the price per this unit (e.g. 'cây'); default base unit.
    """
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    sub = nh[(nh['dt'] >= s) & (nh['dt'] < e) & (nh['name_n'] == norm(name))]
    q = sub['base_qty'].sum()
    if per_unit is not None:
        dm = _b['dm']
        rows = dm[dm['name_n'] == norm(name)]
        if len(rows):
            row = rows.iloc[0]
            if str(per_unit).strip() == str(row['ĐV lớn']).strip():
                q = q / float(row['Hệ số QĐ'])
    return float(sub['ttien'].sum()) / q if q else 0.0
