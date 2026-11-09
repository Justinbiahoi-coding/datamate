from pathlib import Path
OUT = Path('/tmp/s9_024')
PRE = '''import sys, re, unicodedata
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
    return re.sub(r'\\s+', ' ', s).strip()


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
'''
BODY = '''
v = prep(raw if not DEDUPE else raw.drop_duplicates())


def rev(a, b):
    s = v[v['valid'] & (v['dt'] >= pd.Timestamp(a)) & (v['dt'] <= pd.Timestamp(b))]
    return float(s['amt'].sum())


def qrev(name, a, b):
    s = v[(v['name_n'] == norm(name)) & v['valid'] & (v['dt'] >= pd.Timestamp(a)) & (v['dt'] <= pd.Timestamp(b))]
    return float(s['amt'].sum())
'''
S = {
'q_0da07cfbc55f': "RESULT = r0(rev('2025-09-01', '2025-09-30'))\n",
'q_222e5130802b': "RESULT = r0(rev('2025-02-01', '2025-02-28'))\n",
'q_316eb9123dfc': "RESULT = r0(rev('2026-04-01', '2026-04-30'))\n",
'q_342c8720b994': "RESULT = r0(rev('2026-01-01', '2026-03-31'))\n",
'q_464577a14b31': "RESULT = r0(qrev('Lẩu nấm hải sản', '2025-05-01', '2025-05-31'))\n",
'q_5950425c2059': "RESULT = r0(rev('2025-11-01', '2025-11-30'))\n",
'q_678e3a10c525': "RESULT = r0(rev('2025-09-02', '2025-09-02'))\n",
'q_796cdbc9ba34': "RESULT = r0(rev('2025-07-01', '2025-09-30'))\n",
'q_82a889ab0af6': "RESULT = r0(rev('2025-06-01', '2025-06-30'))\n",
'q_9eb6b6467578': "RESULT = r0(rev('2025-08-06', '2025-08-06'))\n",
}
for q, body in S.items():
    for tag in (False, True):
        (OUT / f'{q}_{"T" if tag else "F"}.py').write_text(PRE + f"DEDUPE = {tag}\n" + BODY + body)
print('wrote', len(S)*2)
