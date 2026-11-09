import sys; sys.path.insert(0,'code')
from loader import load_business
from pathlib import Path
import pandas as pd, numpy as np, re, unicodedata
pd.set_option('display.width',250); pd.set_option('display.max_columns',40); pd.set_option('display.max_rows',100)
b=load_business(Path('train/data/biz_109'))
D=b['DuLieuBanHang']
def norm(s):
    return re.sub(r'\s+',' ',unicodedata.normalize('NFD',str(s)).encode('ascii','ignore').decode().lower()).strip()
hd=D['DanhSachHoaDon'].copy()
hd['date']=parse_date(hd['Thời gian'])
print('HD date range', hd['date'].min(), hd['date'].max(), 'nulls', hd['date'].isna().sum())
print(hd['date'].dt.to_period('M').value_counts().sort_index().to_string())
print()
print('Thu gian tao dtype', hd['Thời gian tạo'].dtype, hd['Thời gian tạo'].head().tolist())
print()
# products
sp=D['DanhSachSanPham']
print('Products:'); print(sp[['Mã hàng','Tên hàng','ĐVT','Giá bán','Giá vốn','Nhóm hàng(3 Cấp)']].to_string())
