import sys, unicodedata
sys.path.insert(0,'code')
from loader import load_business
from pathlib import Path
import pandas as pd, numpy as np

def norm(s):
    return unicodedata.normalize('NFC', str(s)).strip().lower()

b = load_business(Path('train/data/biz_112'))
prod = b[[k for k in b if norm(k).startswith('danh')][0]].copy()
d = pd.concat([b['So_chi_tiet_ban_hang_1__all'], b['So_chi_tiet_ban_hang_2026__all']], ignore_index=True)
d['date'] = pd.to_datetime(d['Ngày'].astype(str).str.strip(), format='%d/%m/%Y', errors='coerce')
def money(x):
    return pd.to_numeric(x.astype(str).str.replace(r'[^\d.\-]','',regex=True), errors='coerce')
for c in ['Số lượng','Đơn giá','Thành tiền']:
    d[c+'_n'] = money(d[c])
d['qty'] = pd.to_numeric(d['Số lượng quy đổi'], errors='coerce')
d['status_raw'] = d['Trạng thái'].astype(str).str.strip()
cancel_set = {'cancel','đã hủy đơn','huỷ','hủy','đã hủy'}
return_set = {'trả hàng','hoàn trả','đã trả hàng','trả'}
d['is_cancel'] = d['status_raw'].str.lower().isin(cancel_set)
d['is_return'] = d['status_raw'].str.lower().isin(return_set)
d['ok'] = ~(d['is_cancel']|d['is_return'])
prod['name_n'] = prod['Tên hàng hóa'].map(norm)
d['name_n'] = d['Tên hàng hóa'].map(norm)
if __name__=='__main__':
    print('rows', len(d), 'dates', d['date'].min(), d['date'].max(), 'nat', d['date'].isna().sum())
    print('status', d.groupby('status_raw').size().to_dict())
    print('unmatched names:', sorted(set(d['name_n'])-set(prod['name_n'])))
    print('prod dup names:', prod['name_n'].duplicated().sum())
    print('qty null', d['qty'].isna().sum(), 'thanhtien null', d['Thành tiền_n'].isna().sum())
    print('ordercode unique', d['Mã đơn hàng'].nunique())
    # status per order consistency
    g = d.groupby('Mã đơn hàng')['status_raw'].nunique()
    print('orders multi-status', (g>1).sum())
    print('units', d['Đơn vị tính'].value_counts().to_dict())
    print(prod[['name_n','Nhóm hàng hóa','Đơn vị tính']].to_string())

def canon(s):
    import re
    t = unicodedata.normalize('NFD', str(s))
    t = ''.join(ch for ch in t if unicodedata.category(ch)!='Mn')
    t = t.replace('đ','d').replace('Đ','D')
    return re.sub(r'\s+',' ',unicodedata.normalize('NFC',t).strip().lower())

d['canon'] = d['Tên hàng hóa'].map(canon)
prod['canon'] = prod['Tên hàng hóa'].map(canon)
d = d.merge(prod[['canon','Nhóm hàng hóa','Đơn vị tính']].rename(columns={'Đơn vị tính':'base_unit'}), on='canon', how='left')
