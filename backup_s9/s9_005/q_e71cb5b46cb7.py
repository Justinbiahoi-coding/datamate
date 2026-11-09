import re, unicodedata
hd = DanhSachHoaDon.copy()
hd['date'] = parse_date(hd['Thời gian'])
st = hd['Trạng thái'].astype(str)
hd['valid'] = ~(st.str.contains('hủy|huỷ', case=False, na=False) | st.str.contains('trả hàng|hoàn hàng|trả lại', case=False, na=False))
hd['hour'] = hd['Thời gian tạo'].dt.hour
today = pd.Timestamp(as_of_date)
this_monday = today - pd.Timedelta(days=today.weekday())
prev_monday = this_monday - pd.Timedelta(days=7)
prev_sunday = this_monday - pd.Timedelta(days=1)
m = hd['valid'] & (hd['date'] >= prev_monday) & (hd['date'] <= prev_sunday) & (hd['hour'] >= 14) & (hd['hour'] < 22)
RESULT = int(m.sum())
