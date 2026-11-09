"""Helpers for biz_124 (Excel POS export + notebook)."""
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
    s = str(x).strip().lower().replace('đ', '').replace(' ', '')
    mult = 1.0
    if s.endswith('tr'):
        s = s[:-2].replace(',', '.')
        mult = 1_000_000.0
    elif s.endswith('k'):
        s = s[:-1].replace('.', '').replace(',', '.')
        mult = 1_000.0
    else:
        s = s.replace('.', '').replace(',', '')
    try:
        return float(s) * mult
    except Exception:
        return np.nan


def to_date(x):
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return pd.Timestamp('1899-12-30') + pd.Timedelta(days=float(x))
    if isinstance(x, str) and re.match(r'^\s*\d{5}(\.0+)?\s*$', x):
        return pd.Timestamp('1899-12-30') + pd.Timedelta(days=float(x))
    d = pd.to_datetime(x, errors='coerce', dayfirst=True)
    if pd.isna(d):
        m = re.match(r'^\s*(\d{1,2})\s*thg\s*(\d{1,2})\s*(\d{4})\s*$', str(x), re.I)
        if m:
            try:
                d = pd.Timestamp(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except Exception:
                d = pd.NaT
    if pd.isna(d):
        try:
            d = pd.Timestamp('1899-12-30') + pd.Timedelta(days=float(x))
        except Exception:
            pass
    return d


_b = None


def tables():
    global _b
    if _b is None:
        b = load_business(ROOT / 'train' / 'data' / 'biz_124')

        hd = b['BanHang_HoaDon'].copy()
        hd['dt'] = pd.to_datetime(hd['Giờ tạo đơn'], errors='coerce')
        hd['day'] = hd['dt'].dt.normalize()
        hd['total'] = hd['Tong tien'].map(money)
        hd['paid_field'] = hd['Đã thu'].map(money)
        hd['due_field'] = hd['Còn nợ'].map(money)
        hd['pre_disc'] = hd['Tiền hàng trước giảm'].map(money)
        hd['ck'] = hd['CK'].map(money)
        hd['valid'] = hd['Trạng thái'].isin(['Đã giao', 'Đang vận chuyển'])
        hd['cancelled'] = hd['Trạng thái'] == 'Không giao được'
        hd['returned'] = hd['Trạng thái'] == 'Đổi trả'

        ct = b['BanHang_ChiTietHoaDon'].drop_duplicates().copy()
        ct['rev'] = ct['Thanh tien'].map(money)
        ct['qty'] = pd.to_numeric(ct['SL cơ bản'], errors='coerce')
        ct['cost'] = ct['Giá vốn lúc bán'].map(money)
        ct['slg'] = pd.to_numeric(ct['Slg'], errors='coerce')
        ct['listed'] = ct['Giá niêm yết'].map(money)

        hh = b['BanHang_HangHoa'].copy()
        hh['name_n'] = hh['Món'].map(norm)
        hh['group_n'] = hh['Phân loại'].map(norm)
        smap = hh.drop_duplicates('ma_sp').set_index('ma_sp')
        ct['name_n'] = ct['Ma hang'].map(smap['name_n'])
        ct['group_n'] = ct['Ma hang'].map(smap['group_n'])
        ct['base_unit'] = ct['Ma hang'].map(smap['Đơn vị'])
        ct['cost_now'] = ct['Ma hang'].map(smap['Giá vốn hiện tại'].map(money))

        thuoc = b['BanHang_Thuoc'].copy()
        thuoc['ingredient'] = thuoc['Hoạt chất'].astype(str).map(norm)
        thuoc['rx'] = thuoc['Kê đơn'].astype(str).str.strip().str.upper().isin(['TRUE', '1'])
        tmap = thuoc.drop_duplicates('Mã HH').set_index('Mã HH')
        ct['ingredient'] = ct['Ma hang'].map(tmap['ingredient'])
        ct['rx'] = ct['Ma hang'].map(tmap['rx'])

        ct = ct.merge(hd[['Order ID', 'dt', 'day', 'valid', 'cancelled', 'returned',
                          'Mã NV bán', 'Mã KH mua', 'Nguồn đơn', 'Phương thức TT',
                          'total', 'Trạng thái']],
                      left_on='Mã giao dịch', right_on='Order ID', how='left')

        kh = b['BanHang_KhachHang'].copy()
        kh['rank_n'] = kh['Hạng'].map(norm)
        krank = kh.drop_duplicates('Customer ID').set_index('Customer ID')['rank_n']
        hd['cust_rank'] = hd['Mã KH mua'].map(krank)
        ct['cust_rank'] = ct['Mã KH mua'].map(krank)

        pt = b['BanHang_PhieuThu'].copy()
        pt['dt'] = pd.to_datetime(pt['Thời gian thu'], errors='coerce')
        pt['amount'] = pt['Số tiền thu'].map(money)

        nh = b['SoTay_NhapHang'].copy()
        nh['dt'] = nh['Ngày nhập'].map(to_date)
        nh['name_n'] = nh['Product'].map(norm)
        nh['price'] = nh['Giá nhập'].map(money)
        nh['amount'] = nh['Thành tiền'].map(money)
        nh['qty'] = pd.to_numeric(nh['SL nhập'], errors='coerce')
        nh['line_amount'] = nh['amount'].fillna(nh['price'] * nh['qty'])
        dv = b['BanHang_DonViQuyDoi'].copy()
        dv['factor'] = pd.to_numeric(dv['Bằng'], errors='coerce')
        dvmap = dv.drop_duplicates(['Mã sp', 'Đơn vị']).set_index(['Mã sp', 'Đơn vị'])['factor']
        unit_to_sp = hh.drop_duplicates('ma_sp').set_index('Món')['ma_sp']
        nh['ma_sp'] = nh['Product'].map(hh.drop_duplicates('Món').set_index('Món')['ma_sp'])
        key = pd.MultiIndex.from_arrays([nh['ma_sp'], nh['ĐVT nhập']])
        nh['factor'] = pd.Series(key.map(dvmap), index=nh.index).astype(float)
        nh.loc[nh['factor'].isna(), 'factor'] = 1.0
        nh['base_qty'] = nh['qty'] * nh['factor']

        tk = b['ton_kho'].copy()
        tk['stock'] = pd.to_numeric(tk['Ton kho'], errors='coerce')

        _b = dict(hd=hd, ct=ct, hh=hh, kh=kh, smap=smap, pt=pt, nh=nh, tk=tk, dv=dv)
    return _b


def orders_in(hd, start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    return hd[hd['valid'] & (hd['dt'] >= s) & (hd['dt'] < e)]


def order_rev(ct, hd, start, end):
    ids = set(orders_in(hd, start, end)['Order ID'])
    return ct[ct['Mã giao dịch'].isin(ids)].groupby('Mã giao dịch')['rev'].sum()


def revenue(ct, hd, start, end):
    return float(order_rev(ct, hd, start, end).sum())


def n_orders(hd, start, end):
    return int(orders_in(hd, start, end)['Order ID'].nunique())


def avg_order(ct, hd, start, end):
    r = order_rev(ct, hd, start, end)
    return float(r.sum()) / r.size if r.size else 0.0


def product_rev(ct, hd, start, end, name):
    ids = set(orders_in(hd, start, end)['Order ID'])
    sub = ct[ct['Mã giao dịch'].isin(ids) & (ct['name_n'] == norm(name))]
    return float(sub['rev'].sum())


def product_qty(ct, hd, start, end, name):
    ids = set(orders_in(hd, start, end)['Order ID'])
    sub = ct[ct['Mã giao dịch'].isin(ids) & (ct['name_n'] == norm(name))]
    return float(sub['qty'].sum())


def group_rev(ct, hd, start, end, group):
    ids = set(orders_in(hd, start, end)['Order ID'])
    sub = ct[ct['Mã giao dịch'].isin(ids) & (ct['group_n'] == norm(group))]
    return float(sub['rev'].sum())


def ingredient_rev(ct, hd, start, end, ingredient):
    ids = set(orders_in(hd, start, end)['Order ID'])
    sub = ct[ct['Mã giao dịch'].isin(ids) & (ct['ingredient'] == norm(ingredient))]
    return float(sub['rev'].sum())


def rx_rev(ct, hd, start, end, rx=True):
    ids = set(orders_in(hd, start, end)['Order ID'])
    sub = ct[ct['Mã giao dịch'].isin(ids) & (ct['rx'] == rx)]
    return float(sub['rev'].sum())


def employee_rev(ct, hd, start, end, code):
    ids = set(orders_in(hd, start, end)['Order ID'])
    sub = ct[ct['Mã giao dịch'].isin(ids) & (ct['Mã NV bán'] == code)]
    return float(sub['rev'].sum())


def rank_rev(ct, hd, start, end, rank):
    ids = set(orders_in(hd, start, end)['Order ID'])
    sub = ct[ct['Mã giao dịch'].isin(ids) & (ct['cust_rank'] == norm(rank))]
    return float(sub['rev'].sum())


def orders_at_least(ct, hd, start, end, thr):
    r = order_rev(ct, hd, start, end)
    return int((r >= thr).sum())


def debt_orders(hd, pt, asof):
    """Outstanding debt rows at end of asof (exclude cancelled, COD)."""
    a = pd.Timestamp(asof) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    d = hd[(~hd['cancelled']) & (hd['dt'] <= a) & (hd['Phương thức TT'] != 'Thu hộ (COD)')].copy()
    paid = pt[pt['dt'] <= a].groupby('Mã bill')['amount'].sum()
    d['paid'] = d['Order ID'].map(paid).fillna(0)
    d['out'] = d['total'] - d['paid']
    return d[d['out'] > 0]


def collections(hd, pt, start, end):
    m = pt.merge(hd[['Order ID', 'dt', 'Phương thức TT', 'Trạng thái']],
                 left_on='Mã bill', right_on='Order ID', suffixes=('', '_o'))
    m['lag'] = (m['dt'].dt.normalize() - m['dt_o'].dt.normalize()).dt.days
    s = m[(m['dt'] >= pd.Timestamp(start)) & (m['dt'] < pd.Timestamp(end) + pd.Timedelta(days=1))
          & (m['Phương thức TT'] == 'Ghi nợ') & (m['lag'] > 0) & (m['Trạng thái'] != 'Không giao được')]
    return float(s['amount'].sum())
