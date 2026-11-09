"""Helpers for biz_118 (per-month sales sheets + delivery ledger + catalogue)."""
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


def nfc(s):
    return unicodedata.normalize('NFC', str(s))


def money(s):
    if isinstance(s, (int, float, np.integer, np.floating)) and not isinstance(s, bool):
        return float(s)
    s = nfc(s).strip().lower().replace('đ', '').replace('₫', '')
    if not s or s in ('nan', 'none'):
        return np.nan
    s = s.replace(' ', '').replace(',', '')
    s = re.sub(r'[^0-9.\-]', '', s)
    if s in ('', '-', '.'):
        return np.nan
    try:
        return float(s)
    except Exception:
        return np.nan


def dates(col):
    return pd.to_datetime(pd.Series(col), dayfirst=True, errors='coerce')


_b = None


def table(keypart):
    """Fetch a top-level table whose (NFC) name contains keypart."""
    def get(obj):
        for k, v in obj.items():
            if keypart.lower() in nfc(k).lower():
                return v
        raise KeyError(keypart)
    return get(load_business(ROOT / 'train' / 'data' / 'biz_118'))


def tables():
    global _b
    if _b is None:
        b = load_business(ROOT / 'train' / 'data' / 'biz_118')
        ct = b['So_chi_tiet_ban_hang__all'].copy()
        ct['dt'] = dates(ct['Ngày'])
        st = ct['Trạng thái'].astype(str).str.strip()
        ct['st_norm'] = np.select(
            [st.str.contains('hủy|huỷ|không giao', case=False, na=False),
             st.str.contains('trả', case=False, na=False)],
            ['cancel', 'return'], default='ok')
        ct['ttien'] = ct['Thành tiền'].map(money)
        ct['qty'] = pd.to_numeric(ct['Số lượng'], errors='coerce')
        ct['slqd'] = pd.to_numeric(ct['Số lượng quy đổi'], errors='coerce')
        ct['name_n'] = ct['Tên hàng hóa'].map(norm)
        ct['cust_n'] = ct['Khách hàng'].map(norm)

        sp = None
        for k, v in b.items():
            if 'danh' in nfc(k).lower() and isinstance(v, pd.DataFrame):
                sp = v
                break
        sp = sp.rename(columns={c: nfc(c) for c in sp.columns})
        sp['name_n'] = sp['Tên hàng hóa'].map(norm)
        sp['group_n'] = sp['Nhóm hàng hóa'].map(norm)
        cmap = sp.drop_duplicates('name_n').set_index('name_n')
        ct['unit'] = ct['name_n'].map(cmap['Đơn vị tính'])
        ct['group_n'] = ct['name_n'].map(cmap['group_n'])

        gh = None
        for k, v in b.items():
            if 'giao' in nfc(k).lower() and isinstance(v, pd.DataFrame):
                gh = v
                break
        gh = gh.rename(columns={c: nfc(c) for c in gh.columns}).copy()
        gh['dt'] = dates(gh['Ngày giao hàng'])

        _b = dict(ct=ct, sp=sp, gh=gh)
    return _b


def month_mask(dt, y, m):
    s = pd.Timestamp(year=y, month=m, day=1)
    e = s + pd.offsets.MonthBegin(1)
    return (dt >= s) & (dt < e)


def orders_in(ct, start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    return ct[(ct['st_norm'] == 'ok') & (ct['dt'] >= s) & (ct['dt'] < e)]


def order_rev(ct, start, end):
    sub = orders_in(ct, start, end)
    return sub.groupby('Mã đơn hàng')['ttien'].sum()


def revenue(ct, start, end):
    return float(order_rev(ct, start, end).sum())


def n_orders(ct, start, end):
    return int(order_rev(ct, start, end).size)


def avg_order(ct, start, end):
    r = order_rev(ct, start, end)
    return float(r.sum()) / r.size if r.size else 0.0


def product_rev(ct, start, end, name):
    sub = orders_in(ct, start, end)
    return float(sub.loc[sub['name_n'] == norm(name), 'ttien'].sum())


def product_qty(ct, start, end, name):
    sub = orders_in(ct, start, end)
    return float(sub.loc[sub['name_n'] == norm(name), 'slqd'].sum())


def unit_qty(ct, start, end, unit):
    sub = orders_in(ct, start, end)
    return float(sub.loc[sub['unit'] == unit, 'slqd'].sum())


def group_rev(ct, start, end, group):
    sub = orders_in(ct, start, end)
    return float(sub.loc[sub['group_n'] == norm(group), 'ttien'].sum())


def stale_items(ct, start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    valid = ct[ct['st_norm'] == 'ok']
    before = set(valid.loc[valid['dt'] < s, 'name_n'])
    during = set(valid.loc[(valid['dt'] >= s) & (valid['dt'] < e), 'name_n'])
    return len(before - during)


def cust_counts(ct, start, end, minn):
    sub = orders_in(ct, start, end)
    per = sub.groupby('Mã đơn hàng')['cust_n'].first()
    per = per[~per.isin(['khach le', 'le', 'kl', ''])]
    return int((per.value_counts() >= minn).sum())


def delivery_trips(gh, start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    sub = gh[(gh['dt'] >= s) & (gh['dt'] < e)]
    return int(sub[['Mã đơn hàng', 'Lần giao']].drop_duplicates().shape[0])
