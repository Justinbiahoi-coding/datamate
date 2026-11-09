from pathlib import Path
OUT=Path('/tmp/s9_023')
PRE='''import sys
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
'''
S={
'q_1a7dc79f758c': """
s = v[(v['Hàng bán'] == 'Cánh gà chiên nước mắm') & v['valid'] & (v['dt'] >= pd.Timestamp('2025-01-01')) & (v['dt'] < pd.Timestamp('2025-02-01'))]
RESULT = r0(s['qty'].sum())
""",
'q_252244893f6d': """
s = v[(v['Hàng bán'] == 'Tôm nướng mọi') & (v['dt'] == pd.Timestamp('2026-04-27'))]
RESULT = r0(s['price'].iloc[-1])
""",
'q_6a177988a2d4': """
s = v[v['valid'] & (v['dt'] == pd.Timestamp('2026-05-05'))]
RESULT = r0(s['amt'].sum())
""",
}
for q,body in S.items():
    (OUT/f'{q}.py').write_text(PRE+body)
print('wrote',len(S))
