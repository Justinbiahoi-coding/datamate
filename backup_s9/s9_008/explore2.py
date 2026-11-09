import sys; sys.path.insert(0,'code')
from loader import load_business
from pathlib import Path
import pandas as pd, numpy as np, re
b = load_business(Path('train/data/biz_111'))
dh=b['don_hang'].copy(); ct=b['chi_tiet_don'].copy(); sp=b['san_pham'].copy(); tt=b['thanh_toan'].copy()
exec(open('/tmp/s9_008/parsefn.py').read())
dh['date']=parse(dh['NgayBan']); tt['date']=parse(tt['Thời gian thu'])
m = ct.merge(dh[['Mã chứng từ','date','Xử lý','Phương thức TT','Số KH']], left_on='Ma don', right_on='Mã chứng từ', how='left')
spmap=sp.set_index('SKU')
m['ten']=m['ID SP'].map(spmap['Sản phẩm']); m['nhom']=m['ID SP'].map(spmap['Nhom hang']); m['dvt']=m['ID SP'].map(spmap['Đơn vị'])
m['ten_n']=m['ten'].str.lower().str.strip()
valid = m[~m['Xử lý'].isin(['cancelled','returned'])].copy()
def sub(y,mo): return valid[(valid['date'].dt.year==y)&(valid['date'].dt.month==mo)]
def sz(mo_s,y,mo, only_drink=True):
    x=sub(y,mo)
    mask=x['ten_n'].str.endswith(f'({mo_s.lower()})')
    return x[mask]['SL quy đổi'].sum(), len(x[mask])
for y,mo in [(2026,5),(2025,10),(2025,6)]:
    print('sizeL',y,mo,sz('L',y,mo),'sizeM',sz('M',y,mo))
# product specific
for name,y,mo in [('Sữa tươi trân châu đường đen (L)',2025,7),('Sinh tố xoài (M)',2025,8),('Espresso (double)',2025,6)]:
    x=sub(y,mo); xx=x[x['ten'].str.lower().str.strip()==name.lower()]
    print(name,y,mo,'qty=',xx['SL quy đổi'].sum(),'nlines',len(xx),'rev',xx['T.Tiền'].sum())
# cancelled counts
for y,mo in [(2025,9),(2025,6),(2025,2)]:
    x=dh[(dh['date'].dt.year==y)&(dh['date'].dt.month==mo)&(dh['Xử lý']=='cancelled')]
    print('cancelled',y,mo,len(x))
# day revenue
for d in ['2025-08-13','2025-04-26']:
    x=valid[valid['date']==pd.Timestamp(d)]
    print('rev',d, x['T.Tiền'].sum(), 'orders', x['Mã chứng từ'].nunique())
# orders yesterday
for d in ['2026-07-03','2025-12-29','2025-10-31']:
    day=pd.Timestamp(d)-pd.Timedelta(days=1)
    x=valid[valid['date']==day]
    print('orders yesterday of',d,'=',day.date(), x['Mã chứng từ'].nunique())
# cups yesterday 2026-01-20 -> 2026-01-19, dvt ly
d=pd.Timestamp('2026-01-19')
x=valid[(valid['date']==d)&(valid['dvt']=='ly')]
print('cups 2026-01-19', x['SL quy đổi'].sum(), 'all dvt', valid[valid['date']==d]['SL quy đổi'].sum())
# nhom da xay Feb2025 revenue
x=valid[(valid['date'].dt.year==2025)&(valid['date'].dt.month==2)&(valid['nhom'].str.lower()=='đá xay')]
print('da xay feb2025 rev', x['T.Tiền'].sum())
# debt collections
debt_ids=set(dh[dh['Phương thức TT']=='debt']['Mã chứng từ'])
print('debt orders',len(debt_ids),'cancelled debt',len(debt_ids & set(dh[dh['Xử lý']=='cancelled']['Mã chứng từ'])))
o=dh.set_index('Mã chứng từ')
t=tt.copy(); t['order_date']=t['Số HĐ'].map(o['date']); t['method']=t['Số HĐ'].map(o['Phương thức TT']); t['status']=t['Số HĐ'].map(o['Xử lý'])
for y,mo in [(2026,8),(2025,7),(2025,3)]:
    x=t[(t['date'].dt.year==y)&(t['date'].dt.month==mo)&(t['method']=='debt')&(t['status']!='cancelled')&(t['date']>t['order_date'].fillna(pd.Timestamp('2100-01-01')))]
    print('debt collected',y,mo, x['Tiền'].sum(), 'n',len(x))
