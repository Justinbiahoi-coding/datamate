import pandas as pd
from datetime import datetime, timedelta

as_of_date_str = "2026-03-03"
as_of_dt = datetime.strptime(as_of_date_str, '%Y-%m-%d')
yesterday = (as_of_dt - timedelta(days=1)).strftime('%d/%m/%Y')

# Access the sales detail sheet
df = Bao_cao_ban_hang__So_chi_tiet_ban_hang

# Convert date and filter for yesterday
df['Ngày_dt'] = parse_date(df['Ngày'])
yesterday_df = df[df['Ngày_dt'].dt.strftime('%d/%m/%Y') == yesterday]

# Count unique orders with status "ok" (exclude cancelled and returned)
valid_orders = yesterday_df[yesterday_df['Trạng thái'] == 'ok']['Mã đơn hàng'].nunique()
RESULT = int(valid_orders)
