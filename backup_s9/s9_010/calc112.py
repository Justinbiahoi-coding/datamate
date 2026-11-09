import sys; sys.path.insert(0,'code')
from loader import load_business
from pathlib import Path
import pandas as pd, numpy as np, re, unicodedata

b = load_business(Path('train/data/biz_112'))
hh=[v for k,v in b.items() if k.startswith('Danh')][0].copy()
df=pd.concat([b['So_chi_tiet_ban_hang_1__all'],b['So_chi_tiet_ban_hang_2026__all']],ignore_index=True)

def norm(s):
    s=str(s)
    s=s.replace('đ','d').replace('Đ','D')
    s=unicodedata.normalize('NFD',s).encode('ascii','ignore').decode()
    s=s.lower()
    return re.sub(r'\s+',' ',s).strip()
df['n']=df['Tên hàng hóa'].map(norm)
hh['n']=hh['Tên hàng hóa'].map(norm)
df['dt']=pd.to_datetime(df['Ngày'], dayfirst=True, errors='coerce')
df['amt']=pd.to_numeric(df['Thành tiền'].astype(str).str.replace(',',''),errors='coerce')
df['qty']=pd.to_numeric(df['Số lượng quy đổi'],errors='coerce')
df['price']=pd.to_numeric(df['Đơn giá'].astype(str).str.replace(',',''),errors='coerce')
st=df['Trạng thái'].astype(str).str.lower()
cancel=st.str.contains('hủy|huỷ|cancel',na=False)
ret=st.str.contains('trả|hoàn trả|return',na=False)
print('cancel',cancel.sum(),'ret',ret.sum())
df['valid']=~(cancel|ret)
# group map
gmap=dict(zip(hh['n'],hh['Nhóm hàng hóa']))
df['group']=df['n'].map(gmap)
print('unmatched', sorted(set(df['n'])-set(gmap)))
v=df[df['valid']]
def per(x): return x
print('=== Q1 June2026 days rev>=12m')
jun=v[(v['dt']>='2026-06-01')&(v['dt']<='2026-06-30')]
dr=jun.groupby(jun['dt'].dt.date)['amt'].sum()
print(len(dr), (dr>=12000000).sum())
print('=== Q2 last week 2026-03-09..15 rev')
print(v[(v['dt']>='2026-03-09')&(v['dt']<='2026-03-15')]['amt'].sum())
print('=== Q3 YTD to 2026-05-30')
print(v[(v['dt']>='2026-01-01')&(v['dt']<='2026-05-30')]['amt'].sum())
print('=== Q4 July2026 products >=187 orders')
jl=v[(v['dt']>='2026-07-01')&(v['dt']<='2026-07-31')]
cnt=jl.groupby('n')['Mã đơn hàng'].nunique()
print((cnt>=187).sum(), cnt.sort_values(ascending=False).head(20).to_dict())
print('=== Q5 avg/order Feb2026')
feb=v[(v['dt']>='2026-02-01')&(v['dt']<='2026-02-28')]
print(feb['amt'].sum(), feb['Mã đơn hàng'].nunique(), feb['amt'].sum()/feb['Mã đơn hàng'].nunique())
print('=== Q6 YTD 2026-04-19')
print(v[(v['dt']>='2026-01-01')&(v['dt']<='2026-04-19')]['amt'].sum())
print('=== Q7 Jul2025 group tra sua')
x=v[(v['dt']>='2025-07-01')&(v['dt']<='2025-07-31')]
print(x[x['group']=='trà sữa']['amt'].sum())
print('=== Q8 Jun2026 total')
x=v[(v['dt']>='2026-06-01')&(v['dt']<='2026-06-30')]
print(x['amt'].sum())
print('=== Q9 Jun2025 total')
x=v[(v['dt']>='2025-06-01')&(v['dt']<='2025-06-30')]
print(x['amt'].sum())
print('=== Q10 last week 2025? as_of 2026-06-25 prev week 06-15..21 cups ly')
x=v[(v['dt']>='2026-06-15')&(v['dt']<='2026-06-21')]
print('all qty',x['qty'].sum(),'ly only',x[x['n'].map(lambda s: dict(zip(hh['n'],hh['Đơn vị tính'])).get(s)=='ly')]['qty'].sum())
