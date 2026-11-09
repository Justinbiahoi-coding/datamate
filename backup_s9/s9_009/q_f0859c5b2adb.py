import sys
sys.path.insert(0, '/tmp/s9_007')
import h
import pandas as pd

u = h.t111()
don, tt = u['don'], u['tt']


def repayments(start, end):
    credit = don[(don['Phương thức TT'].astype(str).str.strip() == 'debt') &
                 (don['st_norm'] != 'cancel')][['Mã chứng từ', 'dt']]
    q = tt.merge(credit, left_on='Số HĐ', right_on='Mã chứng từ')
    q = q[(q['dt_x'] >= pd.Timestamp(start)) & (q['dt_x'] < pd.Timestamp(end))]
    q = q[q['dt_x'].dt.normalize() > q['dt_y'].dt.normalize()]
    return int(round(float(q['tien'].sum())))

RESULT = repayments('2025-08-01', '2025-09-01')
