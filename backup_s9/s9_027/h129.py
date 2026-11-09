"""Helpers for biz_129 (same schema family as biz_127)."""
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


def money(x):
    if pd.isna(x):
        return np.nan
    raw = str(x).strip().lower().replace('đ', '').replace(' ', '')
    if raw.endswith('tr'):
        body = raw[:-2].replace(',', '.')
        try:
            return float(body) * 1_000_000.0
        except Exception:
            return np.nan
    s = raw.replace(',', '').replace('.', '')
    try:
        return float(s)
    except Exception:
        return np.nan


_b = None


def tables():
    global _b
    if _b is None:
        b = load_business(ROOT / 'train' / 'data' / 'biz_129')
        dh = b['don_hang'].copy()
        dh['dt'] = pd.to_datetime(dh['Ngày bán'], errors='coerce')
        dh['day'] = dh['dt'].dt.normalize()
        dh['valid'] = dh['Tình trạng đơn'].isin(['completed', 'shipping'])
        dh['cancelled'] = dh['Tình trạng đơn'] == 'cancelled'
        dh['returned'] = dh['Tình trạng đơn'] == 'returned'
        dh['total'] = pd.to_numeric(dh['Phải thu'], errors='coerce')
        dh['paid'] = pd.to_numeric(dh['Thanh toán'], errors='coerce')
        dh['due'] = pd.to_numeric(dh['Dư nợ'], errors='coerce')

        ct = b['chi_tiet_don'].drop_duplicates().copy()
        ct['rev'] = ct['Tiền bán'].map(money)
        ct['qty'] = pd.to_numeric(ct['Quy ra ĐV lẻ'], errors='coerce')
        ct['sl'] = pd.to_numeric(ct['S.L'], errors='coerce')
        ct['discount'] = ct['Giảm giá'].map(money)
        ct['unit_price'] = pd.to_numeric(ct['Giá 1 đv'], errors='coerce')
        sp = b['san_pham'].copy()
        sp['name_n'] = sp['Tên sản phẩm'].map(norm)
        sp['group_n'] = sp['Nhom hang'].map(norm)
        smap = sp.drop_duplicates('Mã HH').set_index('Mã HH')
        ct['name_n'] = ct['Mã hàng bán'].map(smap['name_n'])
        ct['group_n'] = ct['Mã hàng bán'].map(smap['group_n'])
        ct['base_unit'] = ct['Mã hàng bán'].map(smap['Đơn vị tính'])
        ct = ct.merge(dh[['Số phiếu', 'dt', 'day', 'valid', 'cancelled', 'returned',
                          'Tình trạng đơn', 'Hình thức thanh toán', 'Mã khách mua']],
                      left_on='Số CT', right_on='Số phiếu', how='left')

        tt = b['thanh_toan'].copy()
        tt['dt'] = pd.to_datetime(tt['Thời điểm'], errors='coerce')
        tt['amount'] = pd.to_numeric(tt['Tiền'], errors='coerce')

        kh = b['khach_hang'].copy()
        kh['rank_n'] = kh['Nhóm'].map(norm)
        krank = kh.drop_duplicates('Mã khách lẻ/sỉ').set_index('Mã khách lẻ/sỉ')['rank_n']
        dh['cust_rank'] = dh['Mã khách mua'].map(krank)

        _b = dict(dh=dh, ct=ct, sp=sp, smap=smap, tt=tt, kh=kh)
    return _b


def orders_in(dh, start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    return dh[dh['valid'] & (dh['dt'] >= s) & (dh['dt'] < e)]


def order_rev(ct, dh, start, end):
    ids = set(orders_in(dh, start, end)['Số phiếu'])
    return ct[ct['Số CT'].isin(ids)].groupby('Số CT')['rev'].sum()


def revenue(ct, dh, start, end):
    return float(order_rev(ct, dh, start, end).sum())


def n_orders(dh, start, end):
    return int(orders_in(dh, start, end)['Số phiếu'].nunique())


def avg_order(ct, dh, start, end):
    r = order_rev(ct, dh, start, end)
    return float(r.sum()) / r.size if r.size else 0.0


def qrev(ct, dh, start, end, name):
    ids = set(orders_in(dh, start, end)['Số phiếu'])
    sub = ct[ct['Số CT'].isin(ids) & (ct['name_n'] == norm(name))]
    return float(sub['rev'].sum())


def qty(ct, dh, start, end, name):
    ids = set(orders_in(dh, start, end)['Số phiếu'])
    sub = ct[ct['Số CT'].isin(ids) & (ct['name_n'] == norm(name))]
    return float(sub['qty'].sum())


def group_rev(ct, dh, start, end, group):
    ids = set(orders_in(dh, start, end)['Số phiếu'])
    sub = ct[ct['Số CT'].isin(ids) & (ct['group_n'] == norm(group))]
    return float(sub['rev'].sum())


def cancelled_count(dh, start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    d = dh[dh['cancelled'] & (dh['dt'] >= s) & (dh['dt'] < e)]
    return int(d['Số phiếu'].nunique())


def collections(dh, tt, start, end):
    m = tt.merge(dh[['Số phiếu', 'dt', 'Hình thức thanh toán', 'Tình trạng đơn']],
                 left_on='Mã giao dịch', right_on='Số phiếu', suffixes=('', '_o'))
    m['lag'] = (m['dt'].dt.normalize() - m['dt_o'].dt.normalize()).dt.days
    s = m[(m['dt'] >= pd.Timestamp(start)) & (m['dt'] < pd.Timestamp(end) + pd.Timedelta(days=1))
          & (m['Hình thức thanh toán'] == 'debt') & (m['lag'] > 0) & (m['Tình trạng đơn'] != 'cancelled')]
    return float(s['amount'].sum())


def price_on_day(ct, name, day):
    """Unit price per base unit on sold lines of orders placed that day (before discount)."""
    sub = ct[(ct['name_n'] == norm(name)) & (ct['day'] == pd.Timestamp(day))]
    if len(sub) == 0:
        return None
    # price per base unit = Tiền bán / Quy ra ĐV lẻ (before line discount)
    sub = sub.copy()
    sub['per_base'] = (sub['rev'] + sub['discount'].fillna(0)) / sub['qty']
    return float(sub['per_base'].median())


def cash_rev(ct, dh, start, end, method='cash'):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    ids = set(dh[dh['valid'] & (dh['Hình thức thanh toán'] == method)
                 & (dh['dt'] >= s) & (dh['dt'] < e)]['Số phiếu'])
    return float(ct[ct['Số CT'].isin(ids)]['rev'].sum())
