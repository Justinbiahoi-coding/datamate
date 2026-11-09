"""Helpers for biz_126 (flat notebook, no order id -> identical rows count twice)."""
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
    s = str(x).strip().replace('đ', '').replace(',', '').replace('.', '')
    try:
        return float(s)
    except Exception:
        return np.nan


_b = None


def tables():
    global _b
    if _b is None:
        b = load_business(ROOT / 'train' / 'data' / 'biz_126')
        v = b['SoBanHang'].copy()
        v['amt'] = v['Thành tiền (đ)'].map(money)
        v['dt'] = pd.to_datetime(v['Ngày tháng'], errors='coerce', dayfirst=True)
        m = v['dt'].isna()
        v.loc[m, 'dt'] = pd.to_datetime(v.loc[m, 'Ngày tháng'], errors='coerce')
        v['qty'] = pd.to_numeric(v['SL lẻ'], errors='coerce')
        v['name_n'] = v['Ten hang'].map(norm)
        v['valid'] = v['Trạng thái đơn'].isin(['Đã giao', 'đang gửi'])
        _b = dict(v=v)
    return _b


def rev(v, a, b):
    s = v[v['valid'] & (v['dt'] >= pd.Timestamp(a)) & (v['dt'] <= pd.Timestamp(b))]
    return float(s['amt'].sum())


def qty(v, name, a, b):
    s = v[(v['name_n'] == norm(name)) & v['valid'] & (v['dt'] >= pd.Timestamp(a)) & (v['dt'] <= pd.Timestamp(b))]
    return float(s['qty'].sum())


def qrev(v, name, a, b):
    s = v[(v['name_n'] == norm(name)) & v['valid'] & (v['dt'] >= pd.Timestamp(a)) & (v['dt'] <= pd.Timestamp(b))]
    return float(s['amt'].sum())
