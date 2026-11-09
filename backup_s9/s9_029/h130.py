"""Helpers for biz_130 (Excel sales detail books)."""
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
        b = load_business(ROOT / 'train' / 'data' / 'biz_130')
        v = pd.concat([b['So_chi_tiet_ban_hang_1'], b['So_chi_tiet_ban_hang_2']], ignore_index=True)
        v = v[v['Ngày'].notna()].copy()
        v['dt'] = pd.to_datetime(v['Ngày'], errors='coerce', dayfirst=True)
        v['day'] = v['dt'].dt.normalize()
        v['amt'] = pd.to_numeric(v['Thành tiền'].astype(str).str.replace(',', ''), errors='coerce')
        v['qty'] = pd.to_numeric(v['Số lượng quy đổi'], errors='coerce')
        v['sl'] = pd.to_numeric(v['Số lượng'].astype(str).str.replace(' đĩa', '').str.replace(' nồi', '')
                                .str.replace(' phần', '').str.replace(' tô', '').str.replace(' ly', '')
                                .str.replace(' lon', '').str.replace(' chai', '').str.replace(' thùng', '')
                                .str.replace(' két', '').str.replace(' con', '').str.replace(' lần', '')
                                .str.strip(), errors='coerce')
        v['unit_price'] = pd.to_numeric(v['Đơn giá'].astype(str).str.replace(',', ''), errors='coerce')
        v['name_n'] = v['Tên hàng hóa'].map(norm)
        sp = b[next(k for k in b if str(k).startswith('Danh'))].copy()
        sp['name_n'] = sp['Tên hàng hóa'].map(norm)
        sp['group_n'] = sp['Nhóm hàng hóa'].map(norm)
        gmap = sp.drop_duplicates('Tên hàng hóa').set_index('Tên hàng hóa')['group_n']
        v['group_n'] = v['Tên hàng hóa'].map(gmap)
        st = v.groupby('Mã đơn hàng')['Trạng thái'].agg(lambda s: s.dropna().iloc[0] if s.notna().any() else None)
        v['order_status'] = v['Mã đơn hàng'].map(st)
        v['valid'] = v['order_status'].isin(['Đã hoàn thành', 'Đang giao hàng'])
        v['cancelled'] = v['order_status'] == 'Đã hủy'
        _b = dict(v=v, sp=sp)
    return _b


def orders_in(v, start, end):
    s, e = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    return v[v['valid'] & (v['dt'] >= s) & (v['dt'] < e)]


def order_rev(v, start, end):
    s = orders_in(v, start, end)
    return s.groupby('Mã đơn hàng')['amt'].sum()


def revenue(v, start, end):
    return float(orders_in(v, start, end)['amt'].sum())


def n_orders(v, start, end):
    return int(orders_in(v, start, end)['Mã đơn hàng'].nunique())


def avg_order(v, start, end):
    r = order_rev(v, start, end)
    return float(r.sum()) / r.size if r.size else 0.0


def qrev(v, start, end, name):
    s = orders_in(v, start, end)
    return float(s[s['name_n'] == norm(name)]['amt'].sum())


def qty(v, start, end, name):
    s = orders_in(v, start, end)
    return float(s[s['name_n'] == norm(name)]['qty'].sum())


def group_rev(v, start, end, group):
    s = orders_in(v, start, end)
    return float(s[s['group_n'] == norm(group)]['amt'].sum())


def price_on_day(v, name, day):
    s = v[(v['name_n'] == norm(name)) & (v['day'] == pd.Timestamp(day))]
    if len(s) == 0:
        return None
    per = []
    for _, r in s.iterrows():
        if r['qty'] and r['sl']:
            per.append(r['unit_price'] * r['sl'] / r['qty'])
        elif r['qty']:
            per.append(r['amt'] / r['qty'])
    if not per:
        return None
    return float(pd.Series(per).median())


def days_ge(v, start, end, thr):
    s = orders_in(v, start, end)
    day = s.groupby('day')['amt'].sum()
    return int((day >= thr).sum())
