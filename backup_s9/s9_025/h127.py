"""Helpers for biz_127."""
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
    m = re.match(r'^(\d+)tr(\d{0,3})$', raw)
    if m:
        frac = m.group(2)
        return float(m.group(1)) * 1_000_000.0 + (float(frac) * 1000.0 if frac else 0.0)
    m = re.match(r'^(\d+(?:\.\d+)?)tr$', raw)
    if m:
        return float(m.group(1)) * 1_000_000.0
    s = raw.replace(',', '').replace('.', '')
    try:
        return float(s)
    except Exception:
        return np.nan


_b = None


def tables():
    global _b
    if _b is None:
        b = load_business(ROOT / 'train' / 'data' / 'biz_127')
        dh = b['don_hang'].copy()
        dh['dt'] = pd.to_datetime(dh['Ngày'], errors='coerce')
        dh['day'] = dh['dt'].dt.normalize()
        dh['valid'] = dh['Tình trạng'].isin(['completed', 'shipping'])
        dh['cancelled'] = dh['Tình trạng'] == 'cancelled'
        dh['total'] = pd.to_numeric(dh['Tổng đơn'], errors='coerce')

        ct = b['chi_tiet_don'].drop_duplicates().copy()
        ct['rev'] = ct['Amount'].map(money)
        ct['qty'] = pd.to_numeric(ct['Số lượng lẻ'], errors='coerce')
        sp = b['san_pham'].copy()
        sp['name_n'] = sp['Tên SP'].map(norm)
        sp['group_n'] = sp['Danh mục'].map(norm)
        smap = sp.drop_duplicates('Mã sản phẩm bán').set_index('Mã sản phẩm bán')
        ct['name_n'] = ct['Mã mặt hàng'].map(smap['name_n'])
        ct['group_n'] = ct['Mã mặt hàng'].map(smap['group_n'])
        ct['base_unit'] = ct['Mã mặt hàng'].map(smap['Đơn vị cơ bản'])
        ct = ct.merge(dh[['Mã chứng từ', 'dt', 'day', 'valid', 'cancelled', 'Tình trạng',
                          'Trả bằng', 'Loại bán', 'Customer ID']],
                      left_on='Mã đơn hàng', right_on='Mã chứng từ', how='left')

        tt = b['thanh_toan'].copy()
        tt['dt'] = pd.to_datetime(tt['Ngày thu'], errors='coerce')
        tt['amount'] = pd.to_numeric(tt['Giá trị'], errors='coerce')

        _b = dict(dh=dh, ct=ct, sp=sp, smap=smap, tt=tt, kh=b['khach_hang'].copy())
    return _b


def orders_in(dh, start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    return dh[dh['valid'] & (dh['dt'] >= s) & (dh['dt'] < e)]


def order_rev(ct, dh, start, end):
    ids = set(orders_in(dh, start, end)['Mã chứng từ'])
    return ct[ct['Mã đơn hàng'].isin(ids)].groupby('Mã đơn hàng')['rev'].sum()


def revenue(ct, dh, start, end):
    return float(order_rev(ct, dh, start, end).sum())


def n_orders(dh, start, end):
    return int(orders_in(dh, start, end)['Mã chứng từ'].nunique())


def avg_order(ct, dh, start, end):
    r = order_rev(ct, dh, start, end)
    return float(r.sum()) / r.size if r.size else 0.0


def qrev(ct, dh, start, end, name):
    ids = set(orders_in(dh, start, end)['Mã chứng từ'])
    sub = ct[ct['Mã đơn hàng'].isin(ids) & (ct['name_n'] == norm(name))]
    return float(sub['rev'].sum())


def qty(ct, dh, start, end, name):
    ids = set(orders_in(dh, start, end)['Mã chứng từ'])
    sub = ct[ct['Mã đơn hàng'].isin(ids) & (ct['name_n'] == norm(name))]
    return float(sub['qty'].sum())


def cancelled_count(dh, start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    d = dh[dh['cancelled'] & (dh['dt'] >= s) & (dh['dt'] < e)]
    return int(d['Mã chứng từ'].nunique())


def collections(dh, tt, start, end):
    m = tt.merge(dh[['Mã chứng từ', 'dt', 'Trả bằng', 'Tình trạng']],
                 left_on='Số CT', right_on='Mã chứng từ', suffixes=('', '_o'))
    m['lag'] = (m['dt'].dt.normalize() - m['dt_o'].dt.normalize()).dt.days
    s = m[(m['dt'] >= pd.Timestamp(start)) & (m['dt'] < pd.Timestamp(end) + pd.Timedelta(days=1))
          & (m['Trả bằng'] == 'debt') & (m['lag'] > 0) & (m['Tình trạng'] != 'cancelled')]
    return float(s['amount'].sum())
