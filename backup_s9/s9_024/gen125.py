from pathlib import Path
OUT = Path('/tmp/s9_024'); OUT.mkdir(exist_ok=True)
PRE = '''import sys, re, unicodedata
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
    return re.sub(r'\\s+', ' ', s).strip()


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
'''
S = {}
S['q_803a3f18dffc'] = "RESULT = r0(qty('Rau muống xào tỏi', '2025-03-01', '2025-03-31'))\n"
S['q_81cf7ce7dabc'] = "RESULT = r0(rev('2025-04-01', '2025-06-30'))\n"
S['q_82cc21bcd784'] = "RESULT = r0(rev('2026-04-01', '2026-04-30'))\n"
S['q_88206fe54899'] = "RESULT = r0(rev('2026-01-01', '2026-01-31'))\n"
S['q_8f16268d281c'] = "RESULT = r0(rev('2026-04-14', '2026-04-14'))\n"
S['q_a64113ee527a'] = "RESULT = r0(qty('Cơm chiên hải sản', '2026-04-01', '2026-04-30'))\n"
S['q_a9305e207d35'] = "RESULT = ndays('2025-07-01', '2025-09-30')\n"
S['q_aadffbaec4f0'] = "RESULT = r0(rev('2025-01-01', '2025-01-31'))\n"
S['q_afbb2701fb2e'] = "RESULT = r0(rev('2026-01-17', '2026-01-17'))\n"
S['q_bbabfdd1ebd7'] = "RESULT = r0(qrev('Cơm chiên dương châu', '2025-03-01', '2025-03-31'))\n"
S['q_bd5285a7fb12'] = "RESULT = ndays('2025-05-04', '2025-05-04')\n"
S['q_c282d9a0161c'] = "RESULT = r0(qty('Sụn gà rang muối', '2025-11-01', '2025-11-30'))\n"
S['q_cfea4d2c4f43'] = "RESULT = ndays('2025-01-01', '2025-03-31')\n"
S['q_e05074e520bc'] = "RESULT = r0(rev('2025-09-10', '2025-09-10'))\n"
S['q_f8237f56fae8'] = "RESULT = r0(rev('2025-06-07', '2025-06-07'))\n"
for q, body in S.items():
    (OUT / f'{q}.py').write_text(PRE + body)
print('wrote', len(S))
