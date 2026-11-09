import sys, re, unicodedata
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/Users/buivanthien/Learn/zalo chelen/datamate/code')
from pathlib import Path
import pandas as pd
from loader import load_business

b = load_business(Path('/Users/buivanthien/Learn/zalo chelen/datamate/train/data/biz_125'))
v = b['ban_hang'].copy()


def norm(s):
    s = str(s).lower().replace('đ', 'd')
    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', s).strip()


def money(x):
    return float(str(x).replace(',', '').replace('đ', '').strip())


v['dt'] = pd.to_datetime(v['Ngày bán'], errors='coerce', dayfirst=True)
v['amt'] = v['Amount'].map(money)
v['qty'] = pd.to_numeric(v['Số lượng lẻ'], errors='coerce')
v['name_n'] = v['Hàng bán'].map(norm)
v['valid'] = v['Trạng thái xử lý'].isin(['Đã hoàn thành', 'Đang xử lý'])


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def rev(a, b):
    s = v[v['valid'] & (v['dt'] >= pd.Timestamp(a)) & (v['dt'] <= pd.Timestamp(b))]
    return float(s['amt'].sum())


def qty(name, a, b):
    s = v[(v['name_n'] == norm(name)) & v['valid'] & (v['dt'] >= pd.Timestamp(a)) & (v['dt'] <= pd.Timestamp(b))]
    return float(s['qty'].sum())


def qrev(name, a, b):
    s = v[(v['name_n'] == norm(name)) & v['valid'] & (v['dt'] >= pd.Timestamp(a)) & (v['dt'] <= pd.Timestamp(b))]
    return float(s['amt'].sum())


def ndays(a, b):
    s = v[v['valid'] & (v['dt'] >= pd.Timestamp(a)) & (v['dt'] <= pd.Timestamp(b))]
    return int(s['Số phiếu'].nunique())
RESULT = ndays('2025-01-01', '2025-03-31')
