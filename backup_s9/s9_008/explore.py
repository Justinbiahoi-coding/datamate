import sys; sys.path.insert(0,'code')
from loader import load_business
from pathlib import Path
import pandas as pd, numpy as np
pd.set_option('display.width',250); pd.set_option('display.max_columns',60)
b = load_business(Path('train/data/biz_111'))
dh=b['don_hang'].copy(); ct=b['chi_tiet_don'].copy(); sp=b['san_pham'].copy(); tt=b['thanh_toan'].copy()
def parse(series):
    import re
    s=series.astype(str).str.strip()
    out=pd.Series(pd.NaT,index=series.index,dtype='datetime64[ns]')
    num=pd.to_numeric(s,errors='coerce'); m=num.notna()&(num>1000)&(num<100000)
    out[m]=pd.Timestamp('1899-12-30')+pd.to_timedelta(num[m],unit='D')
    rest=~m
    if rest.any():
        ss=s[rest]; idx=ss.index
        iso=ss.str.match(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}',na=False)
        if iso.any(): out.loc[idx[iso]]=pd.to_datetime(ss[iso].str.replace('/','-'),yearfirst=True,errors='coerce')
        dmy=~iso&ss.str.match(r'^\d{1,2}[-/]\d{1,2}[-/]\d{4}',na=False)
        if dmy.any(): out.loc[idx[dmy]]=pd.to_datetime(ss[dmy],dayfirst=True,errors='coerce')
        vn=~iso&~dmy&ss.str.contains('thg',case=False,na=False)
        if vn.any():
            def pv(x):
                import re
                mm=re.match(r'(\d+)\s+thg\s+(\d+)\s+(\d{4})',x,re.I)
                if mm:
                    try: return pd.Timestamp(int(mm.group(3)),int(mm.group(2)),int(mm.group(1)))
                    except: return pd.NaT
                return pd.NaT
            out.loc[idx[vn]]=ss[vn].apply(pv)
        other=~iso&~dmy&~vn
        if other.any(): out.loc[idx[other]]=pd.to_datetime(ss[other],dayfirst=True,errors='coerce')
    return out
dh['date']=parse(dh['NgayBan'])
tt['date']=parse(tt['Thời gian thu'])
print('dh date range',dh['date'].min(),dh['date'].max(),'NaT',dh['date'].isna().sum())
print('tt date range',tt['date'].min(),tt['date'].max(),'NaT',tt['date'].isna().sum())
print('dh dup ids',dh['Mã chứng từ'].duplicated().sum(),'n unique',dh['Mã chứng từ'].nunique())
print('ct rows',len(ct),'dup full',ct.duplicated().sum())
print('ct Ma don not in dh', (~ct['Ma don'].isin(dh['Mã chứng từ'])).sum())
print('ct na ma don', ct['Ma don'].isna().sum())
# orders per status
print(dh.groupby('Xử lý')['Mã chứng từ'].nunique())
# check T.Tiền vs sum group
g=ct.groupby('Ma don')['T.Tiền'].sum()
m=dh.set_index('Mã chứng từ')['Tổng bill']
cmp=pd.DataFrame({'lines':g,'bill':m})
cmp['diff']=cmp['bill']-cmp['lines']
print('bill-vs-lines diff stats'); print(cmp['diff'].describe())
print('n diff!=0',(cmp['diff']!=0).sum())
print(cmp[cmp['diff']!=0].head(10))
# SL dtype issues
print('SL samples', ct['SL'].astype(str).str.extract(r'([^\d.,])')[0].dropna().value_counts().head(10))
print('Don vi tinh', ct['Đơn vị (tính)'].value_counts())

# ---- merged line-level
m = ct.merge(dh[['Mã chứng từ','date','Xử lý','Phương thức TT','Số KH']], left_on='Ma don', right_on='Mã chứng từ', how='left')
m['sku']=m['ID SP']
spmap=sp.set_index('SKU')
m['ten']=m['sku'].map(spmap['Sản phẩm']); m['nhom']=m['sku'].map(spmap['Nhom hang']); m['dvt']=m['sku'].map(spmap['Đơn vị'])
valid = m[~m['Xử lý'].isin(['cancelled','returned'])]
def rev(y,mo): 
    x=valid[(valid['date'].dt.year==y)&(valid['date'].dt.month==mo)]
    return x['T.Tiền'].sum()
for y,mo in [(2025,1),(2025,6),(2025,9),(2026,3),(2026,4),(2026,5)]:
    x=valid[(valid['date'].dt.year==y)&(valid['date'].dt.month==mo)]
    n=x['Mã chứng từ'].nunique()
    print(f'{y}-{mo:02d} rev={rev(y,mo)} orders={n} avg={rev(y,mo)/n if n else None}')
# price espresso single 2025-01-11
e=m[(m['sku']=='SP0009')&(m['date']==pd.Timestamp('2025-01-11'))]
print('ESPRESSO 11/01/2025:'); print(e[['Ma don','SL quy đổi','Giá đơn vị','T.Tiền','Xử lý']].to_string())
