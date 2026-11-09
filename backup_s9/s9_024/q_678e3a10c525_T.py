import sys, re, unicodedata
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/Users/buivanthien/Learn/zalo chelen/datamate/code')
from pathlib import Path
import pandas as pd
from loader import load_business

b = load_business(Path('/Users/buivanthien/Learn/zalo chelen/datamate/train/data/biz_126'))
raw = b['SoBanHang'].copy()


def norm(s):
    s = str(s).lower().replace('đ', 'd')
    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', s).strip()


def money(x):
    if pd.isna(x):
        return float('nan')
    s = str(x).strip().replace('đ', '').replace(',', '').replace('.', '')
    try:
        return float(s)
    except Exception:
        return float('nan')


def prep(df):
    v = df.copy()
    v['amt'] = v['Thành tiền (đ)'].map(money)
    v['dt'] = pd.to_datetime(v['Ngày tháng'], errors='coerce', dayfirst=True)
    m = v['dt'].isna()
    v.loc[m, 'dt'] = pd.to_datetime(v.loc[m, 'Ngày tháng'], errors='coerce')
    v['name_n'] = v['Ten hang'].map(norm)
    v['valid'] = v['Trạng thái đơn'].isin(['Đã giao', 'đang gửi'])
    return v


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
DEDUPE = True

v = prep(raw if not DEDUPE else raw.drop_duplicates())


def rev(a, b):
    s = v[v['valid'] & (v['dt'] >= pd.Timestamp(a)) & (v['dt'] <= pd.Timestamp(b))]
    return float(s['amt'].sum())


def qrev(name, a, b):
    s = v[(v['name_n'] == norm(name)) & v['valid'] & (v['dt'] >= pd.Timestamp(a)) & (v['dt'] <= pd.Timestamp(b))]
    return float(s['amt'].sum())
RESULT = r0(rev('2025-09-02', '2025-09-02'))
