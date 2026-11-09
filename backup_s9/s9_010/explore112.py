import sys; sys.path.insert(0,'code')
from loader import load_business
from pathlib import Path
import pandas as pd, numpy as np, re, unicodedata

b = load_business(Path('train/data/biz_112'))
hh=[v for k,v in b.items() if k.startswith('Danh')][0].copy()
df=pd.concat([b['So_chi_tiet_ban_hang_1__all'],b['So_chi_tiet_ban_hang_2026__all']],ignore_index=True)

def norm(s):
    s=str(s)
    s=unicodedata.normalize('NFD',s).encode('ascii','ignore').decode()
    s=s.lower()
    s=re.sub(r'\s+',' ',s).strip()
    return s
for c in ['Tên hàng hóa']:
    print(c, df[c].map(norm).nunique())
# join to product list by norm name
hh['n']=hh['Tên hàng hóa'].map(norm)
# check duplicates in hh names
print('hh dup names', hh['n'].duplicated().sum())
m = hh.set_index('n')
df['n']=df['Tên hàng hóa'].map(norm)
print('unmatched df names:', sorted(set(df['n'])-set(hh['n'])))
print('groups', hh['Nhóm hàng hóa'].unique())
print(df[df['Đơn vị tính']=='hộp'][['Tên hàng hóa','Số lượng','Số lượng quy đổi','Đơn giá','Thành tiền']].head(10).to_string())
