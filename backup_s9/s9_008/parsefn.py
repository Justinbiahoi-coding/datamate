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
