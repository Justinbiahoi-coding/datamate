"""Helpers for biz_121 (pharmacy orders + products + lots + purchases)."""
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


def tables():
    global _b
    if _b is None:
        b = load_business(ROOT / 'train' / 'data' / 'biz_121')
        D = b['DuLieuXuat']
        ct = b['DonHang_ChiTiet'].copy()
        # merged-cell export: order info only on the first line of each order
        for c in ['Mã đơn hàng', 'Ngày đặt hàng', 'Trạng thái đơn hàng', 'Tên khách hàng']:
            ct[c] = ct[c].ffill()
        ct['dt'] = dates(ct['Ngày đặt hàng'])
        st = ct['Trạng thái đơn hàng'].astype(str).str.strip()
        ct['st_norm'] = np.select(
            [st.str.contains('hủy|huỷ|không giao', case=False, na=False),
             st.str.contains('hoàn hàng|trả', case=False, na=False)],
            ['cancel', 'return'], default='ok')
        ct['ttien'] = ct['Tổng tiền'].map(money)
        ct['qty'] = pd.to_numeric(ct['Số lượng sản phẩm'], errors='coerce')
        ct['name_n'] = ct['Tên sản phẩm'].map(norm)
        ct['unit'] = ct['Đơn vị tính'].astype(str).str.strip()
        ct['cust_n'] = ct['Tên khách hàng'].map(norm)

        sp = D['DanhSachSanPham'].copy()
        sp['name_n'] = sp['Tên sản phẩm'].map(norm)
        sp['group_n'] = sp['Loại sản phẩm'].map(norm)
        cmap = sp.drop_duplicates('name_n').set_index('name_n')
        ct['sku'] = ct['name_n'].map(cmap['Mã SKU'])
        ct['base_unit'] = ct['name_n'].map(cmap['Đơn vị'])
        ct['group_n'] = ct['name_n'].map(cmap['group_n'])

        qd = D['DanhSachQuyDoi'].copy()
        qd['name_n'] = qd['Tên sản phẩm'].map(norm)
        qd['factor'] = pd.to_numeric(qd['Tỉ lệ quy đổi'], errors='coerce')
        qmap = qd.drop_duplicates(['name_n', 'Đơn vị quy đổi']).set_index(['name_n', 'Đơn vị quy đổi'])
        key = pd.MultiIndex.from_arrays([ct['name_n'], ct['unit']])
        ct['factor'] = ct.set_index(key).index.map(qmap['factor']).values
        ct['factor'] = pd.to_numeric(ct['factor'], errors='coerce').fillna(1.0)
        ct['base_qty'] = ct['qty'] * ct['factor']

        thuoc = D['DanhSachThuoc'].copy()
        thuoc['sku'] = thuoc['Mã SKU'].astype(str).str.strip()
        thuoc['ingredient'] = thuoc['Hoạt chất'].astype(str).map(norm)
        thuoc['rx'] = thuoc['Thuốc kê đơn'].astype(str).str.strip().str.upper().isin(['TRUE', '1', 'CÓ'])
        tmap = thuoc.drop_duplicates('sku').set_index('sku')
        ct['ingredient'] = ct['sku'].map(tmap['ingredient'])
        ct['rx'] = ct['sku'].map(tmap['rx'])

        # returned quantities per order (base units)
        lo = D['DonHang_Lo'].copy()
        lo['ret'] = pd.to_numeric(lo['Số lượng trả'], errors='coerce').fillna(0)
        ret_orders = set(lo.loc[lo['ret'] > 0, 'Mã đơn hàng'])
        ct['order_valid'] = (ct['st_norm'] == 'ok') & ~ct['Mã đơn hàng'].isin(ret_orders)

        nh = b['DuLieuXuat']['DonNhapHang'].copy()
        nh['dt'] = dates(nh['Ngày nhập'])
        nct = D['DonNhapHang_ChiTiet'].copy()
        nct['q'] = pd.to_numeric(nct['Số lượng nhập'], errors='coerce')
        nct = nct.merge(nh[['Mã đơn nhập', 'dt']], on='Mã đơn nhập', how='left')
        nct['sku'] = nct['Mã SKU'].astype(str).str.strip()

        _b = dict(ct=ct, sp=sp, qd=qd, thuoc=thuoc, lo=lo, nh=nh, nct=nct)
    return _b


def month_mask(dt, y, m):
    s = pd.Timestamp(year=y, month=m, day=1)
    e = s + pd.offsets.MonthBegin(1)
    return (dt >= s) & (dt < e)


def orders_in(ct, start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    return ct[ct['order_valid'] & (ct['dt'] >= s) & (ct['dt'] < e)]


def order_rev(ct, start, end):
    return orders_in(ct, start, end).groupby('Mã đơn hàng')['ttien'].sum()


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
    return float(sub.loc[sub['name_n'] == norm(name), 'base_qty'].sum())


def group_rev(ct, start, end, group):
    sub = orders_in(ct, start, end)
    return float(sub.loc[sub['group_n'] == norm(group), 'ttien'].sum())


def ingredient_rev(ct, start, end, ingredient):
    sub = orders_in(ct, start, end)
    return float(sub.loc[sub['ingredient'] == norm(ingredient), 'ttien'].sum())


def rx_rev(ct, start, end, rx=True):
    sub = orders_in(ct, start, end)
    return float(sub.loc[sub['rx'] == rx, 'ttien'].sum())


def stale_items(ct, start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    valid = ct[ct['order_valid']]
    before = set(valid.loc[valid['dt'] < s, 'name_n'])
    during = set(valid.loc[(valid['dt'] >= s) & (valid['dt'] < e), 'name_n'])
    return len(before - during)


def cust_counts(ct, start, end, minn):
    sub = orders_in(ct, start, end)
    per = sub.groupby('Mã đơn hàng')['cust_n'].first()
    per = per[~per.isin(['khach le', 'le', 'kl', ''])]
    return int((per.value_counts() >= minn).sum())


def stock_now(ct, nct, name):
    """Base-unit stock: purchased - taken from lots + returned to lots."""
    n = norm(name)
    skus = ct.loc[ct['name_n'] == n, 'sku'].dropna()
    if not len(skus):
        return 0.0
    sku = skus.iloc[0]
    lots = set(nct.loc[nct['sku'] == sku, 'Mã lô'])
    bought = float(nct.loc[nct['sku'] == sku, 'q'].sum())
    lo = _b['lo']
    sub = lo[lo['Mã lô'].isin(lots)]
    sold = float(pd.to_numeric(sub['Số lượng'], errors='coerce').fillna(0).sum())
    ret = float(sub['ret'].sum())
    return bought - sold + ret
