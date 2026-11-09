"""Helpers for biz_123 (POS sqlite export)."""
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


_b = None


def tables():
    global _b
    if _b is None:
        b = load_business(ROOT / 'train' / 'data' / 'biz_123')
        dh = b['don_hang'].copy()
        dh['dt'] = pd.to_datetime(dh['ThoiGianLap'], errors='coerce')
        dh['valid'] = dh['TinhTrang'].isin(['completed', 'shipping'])

        ct = b['chi_tiet_don'].drop_duplicates().copy()
        ct['name_n'] = None
        sp = b['san_pham'].copy()
        sp['name_n'] = sp['TenGoi'].map(norm)
        smap = sp.drop_duplicates('MaHangHoa').set_index('MaHangHoa')
        ct['name_n'] = ct['MaHangHoa'].map(smap['name_n'])
        ct['group_n'] = ct['MaHangHoa'].map(smap['DanhMuc'].map(norm))
        ct['base_unit'] = ct['MaHangHoa'].map(smap['DonViCoSo'])

        thuoc = b['thong_tin_thuoc'].copy()
        thuoc['ingredient'] = thuoc['ThanhPhanChinh'].astype(str).map(norm)
        thuoc['rx'] = thuoc['BanTheoDon'].astype(str).str.strip().str.upper().isin(['TRUE', '1'])
        tmap = thuoc.drop_duplicates('MaHangHoa').set_index('MaHangHoa')
        ct['ingredient'] = ct['MaHangHoa'].map(tmap['ingredient'])
        ct['rx'] = ct['MaHangHoa'].map(tmap['rx'])

        ct = ct.merge(dh[['MaHoaDon', 'dt', 'valid', 'MaNhanVien', 'MaKhachHang',
                          'KenhBanHang', 'PhuongThucTT', 'TongThanhToan', 'TinhTrang']],
                      on='MaHoaDon', how='left')

        kh = b['khach_hang'].copy()
        kh['type_n'] = kh['LoaiKhachHang'].map(norm)
        ktype = kh.drop_duplicates('MaKhachHang').set_index('MaKhachHang')['type_n']
        ct['cust_type'] = ct['MaKhachHang'].map(ktype)

        tt = b['thanh_toan'].copy()
        tt['dt'] = pd.to_datetime(tt['NgayGioThu'], errors='coerce')

        pn = b['phieu_nhap'].copy()
        pn['dt'] = pd.to_datetime(pn['NgayNhapKho'], errors='coerce')
        ctn = b['chi_tiet_nhap'].copy()
        ctn['name_n'] = ctn['MaHangHoa'].map(smap['name_n'])
        dv = b['don_vi_sp'].copy()
        dv['factor'] = pd.to_numeric(dv['HeSoQuyDoi'], errors='coerce')
        dvmap = dv.drop_duplicates(['MaHangHoa', 'DonViTinh']).set_index(['MaHangHoa', 'DonViTinh'])['factor']
        key = pd.MultiIndex.from_arrays([ctn['MaHangHoa'], ctn['DonViTinh']])
        ctn['factor'] = pd.Series(key.map(dvmap), index=ctn.index).astype(float).fillna(1.0)
        ctn['base_qty'] = pd.to_numeric(ctn['SL'], errors='coerce') * ctn['factor']
        ctn = ctn.merge(pn[['MaPhieuNhap', 'dt']], on='MaPhieuNhap', how='left')

        tk = b['the_kho'].copy()
        tk['dt'] = pd.to_datetime(tk['NgayGioPhatSinh'], errors='coerce')

        lsg = b['lich_su_gia'].copy()
        lsg['dt'] = pd.to_datetime(lsg['NgayApDung'], errors='coerce')

        _b = dict(dh=dh, ct=ct, sp=sp, kh=kh, smap=smap, tt=tt, pn=pn, ctn=ctn, dv=dv, tk=tk, lsg=lsg)
    return _b


def orders_in(dh, start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    return dh[dh['valid'] & (dh['dt'] >= s) & (dh['dt'] < e)]


def order_rev(ct, dh, start, end):
    ids = set(orders_in(dh, start, end)['MaHoaDon'])
    sub = ct[ct['MaHoaDon'].isin(ids)]
    return sub.groupby('MaHoaDon')['TriGia'].sum()


def revenue(ct, dh, start, end):
    return float(order_rev(ct, dh, start, end).sum())


def n_orders(dh, start, end):
    return int(orders_in(dh, start, end)['MaHoaDon'].nunique())


def avg_order(ct, dh, start, end):
    r = order_rev(ct, dh, start, end)
    return float(r.sum()) / r.size if r.size else 0.0


def product_rev(ct, dh, start, end, name):
    ids = set(orders_in(dh, start, end)['MaHoaDon'])
    sub = ct[ct['MaHoaDon'].isin(ids) & (ct['name_n'] == norm(name))]
    return float(sub['TriGia'].sum())


def product_qty(ct, dh, start, end, name):
    ids = set(orders_in(dh, start, end)['MaHoaDon'])
    sub = ct[ct['MaHoaDon'].isin(ids) & (ct['name_n'] == norm(name))]
    return float(pd.to_numeric(sub['SLQuyDoi'], errors='coerce').sum())


def group_rev(ct, dh, start, end, group):
    ids = set(orders_in(dh, start, end)['MaHoaDon'])
    sub = ct[ct['MaHoaDon'].isin(ids) & (ct['group_n'] == norm(group))]
    return float(sub['TriGia'].sum())


def ingredient_rev(ct, dh, start, end, ingredient):
    ids = set(orders_in(dh, start, end)['MaHoaDon'])
    sub = ct[ct['MaHoaDon'].isin(ids) & (ct['ingredient'] == norm(ingredient))]
    return float(sub['TriGia'].sum())


def rx_rev(ct, dh, start, end, rx=True):
    ids = set(orders_in(dh, start, end)['MaHoaDon'])
    sub = ct[ct['MaHoaDon'].isin(ids) & (ct['rx'] == rx)]
    return float(sub['TriGia'].sum())


def employee_rev(ct, dh, start, end, name):
    ids = set(orders_in(dh, start, end)['MaHoaDon'])
    sub = ct[ct['MaHoaDon'].isin(ids) & (ct['MaNhanVien'] == name)]
    return float(sub['TriGia'].sum())


def cust_type_rev(ct, dh, start, end, ctype):
    ids = set(orders_in(dh, start, end)['MaHoaDon'])
    sub = ct[ct['MaHoaDon'].isin(ids) & (ct['cust_type'] == norm(ctype))]
    return float(sub['TriGia'].sum())


def orders_at_least(ct, dh, start, end, thr):
    r = order_rev(ct, dh, start, end)
    return int((r >= thr).sum())


def debt_at(dh, tt, asof, older_than=None, exclude_channel=None):
    """Outstanding debt of non-cancelled, non-COD orders at end of asof."""
    a = pd.Timestamp(asof) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    d = dh[dh['TinhTrang'] != 'cancelled'].copy()
    d = d[d['dt'] <= a]
    if exclude_channel:
        d = d[~d['KenhBanHang'].isin(exclude_channel)]
    d = d[d['PhuongThucTT'] != 'cod']
    if older_than is not None:
        d = d[d['dt'] < pd.Timestamp(asof) - pd.Timedelta(days=older_than)]
    paid = tt[tt['dt'] <= a].groupby('MaHoaDon')['SoTienThu'].sum()
    d['paid'] = d['MaHoaDon'].map(paid).fillna(0)
    out = d['TongThanhToan'] - d['paid']
    return float(out[out > 0].sum())


def inventory_value(ct, dh, tk, sp, asof):
    """Stock quantity at asof x standard cost (GiaVonHang)."""
    a = pd.Timestamp(asof) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    t = tk[tk['dt'] <= a].sort_values('dt').groupby('MaHangHoa').tail(1)
    cost = sp.drop_duplicates('MaHangHoa').set_index('MaHangHoa')['GiaVonHang']
    t['cost'] = t['MaHangHoa'].map(cost)
    return float((pd.to_numeric(t['TonCuoi'], errors='coerce') * t['cost']).sum())


def purchase_avg(ctn, name, start, end, per_unit=None):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    sub = ctn[(ctn['dt'] >= s) & (ctn['dt'] < e) & (ctn['name_n'] == norm(name))].copy()
    total = (pd.to_numeric(sub['SL'], errors='coerce') * pd.to_numeric(sub['DonGiaNhap'], errors='coerce')).sum()
    q = sub['base_qty'].sum()
    if per_unit is not None:
        # convert base quantity to the requested unit using the product's unit list
        prod = sub['MaHangHoa'].iloc[0]
        f = _b['dv']
        rows = f[(f['MaHangHoa'] == prod) & (f['DonViTinh'] == per_unit)]
        if len(rows):
            q = q / float(rows.iloc[0]['factor'])
    return float(total) / q if q else 0.0
