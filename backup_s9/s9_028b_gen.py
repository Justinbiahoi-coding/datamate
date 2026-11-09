from pathlib import Path
OUT = Path('/tmp/s9_028'); OUT.mkdir(exist_ok=True)
PRE = '''import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, '/Users/buivanthien/Learn/zalo chelen/datamate/code')
from pathlib import Path
import pandas as pd
from loader import load_business

b = load_business(Path('/Users/buivanthien/Learn/zalo chelen/datamate/train/data/biz_130'))
v = pd.concat([b['So_chi_tiet_ban_hang_1'], b['So_chi_tiet_ban_hang_2']], ignore_index=True)
v = v[v['Ngày'].notna()].copy()
v['dt'] = pd.to_datetime(v['Ngày'], errors='coerce', dayfirst=True)
v['amt'] = pd.to_numeric(v['Thành tiền'].astype(str).str.replace(',', ''), errors='coerce')
v['qty'] = pd.to_numeric(v['Số lượng quy đổi'], errors='coerce')
st = v.groupby('Mã đơn hàng')['Trạng thái'].agg(lambda s: s.dropna().iloc[0] if s.notna().any() else None)
valid = set(st[st.isin(['Đã hoàn thành', 'Đang giao hàng'])].index)


def r0(x):
    return int(Decimal(str(float(x))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def rev(a, bb):
    s = v[v['Mã đơn hàng'].isin(valid) & (v['dt'] >= pd.Timestamp(a)) & (v['dt'] <= pd.Timestamp(bb))]
    return float(s['amt'].sum())


def norders(a, bb):
    s = v[v['Mã đơn hàng'].isin(valid) & (v['dt'] >= pd.Timestamp(a)) & (v['dt'] <= pd.Timestamp(bb))]
    return int(s['Mã đơn hàng'].nunique())
'''
S = {
'q_18f8cdf43ae0': "RESULT = r0(rev('2026-01-01', '2026-05-28'))\n",
'q_19b422be1d9b': "RESULT = norders('2025-06-16', '2025-06-22')\n",
'q_229c79268628': """s = v[v['Mã đơn hàng'].isin(valid) & (v['dt'] >= pd.Timestamp('2026-03-01')) & (v['dt'] < pd.Timestamp('2026-04-01'))]
day = s.groupby(s['dt'].dt.normalize())['amt'].sum()
RESULT = int((day >= 53000000).sum())
""",
}
for q, body in S.items():
    (OUT / f'{q}.py').write_text(PRE + body)
print('wrote', len(S))
