import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/Users/buivanthien/Learn/zalo chelen/datamate/code')
from pathlib import Path
import pandas as pd
from loader import load_business

b = load_business(Path('/Users/buivanthien/Learn/zalo chelen/datamate/train/data/biz_125'))
v = b['ban_hang'].copy()


def money(x):
    return float(str(x).replace(',', '').replace('đ', '').strip())


v['dt'] = pd.to_datetime(v['Ngày bán'], errors='coerce', dayfirst=True)
v['amt'] = v['Amount'].map(money)
v['price'] = v['Giá 1 đv'].map(money)
v['qty'] = pd.to_numeric(v['Số lượng lẻ'], errors='coerce')
v['valid'] = v['Trạng thái xử lý'].isin(['Đã hoàn thành', 'Đang xử lý'])


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

s = v[(v['Hàng bán'] == 'Cánh gà chiên nước mắm') & v['valid'] & (v['dt'] >= pd.Timestamp('2025-01-01')) & (v['dt'] < pd.Timestamp('2025-02-01'))]
RESULT = r0(s['qty'].sum())
