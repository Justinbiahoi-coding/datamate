from pathlib import Path
OUT = Path('/tmp/s9_023')
PRE = open(OUT/'q_a149a00151dd.py').read().split("RESULT =")[0]
for q, body in {
 'q_a149a00151dd': "RESULT = r0(net_profit(2025, 6))\n",
 'q_c2d367ddde3f': "RESULT = r0(net_profit(2025, 7))\n",
 'q_eaf0d3e319f0': """name = 'Siro ăn ngon Ích Nhi Plus chai 100ml'
lsg = _b['BanHang_LichSuGia'].copy()
lsg['dt'] = pd.to_datetime(lsg['Ngày áp dụng'], errors='coerce')
spid = hh[hh['Món'].map(H.norm) == H.norm(name)]['ma_sp'].iloc[0]
h = lsg[(lsg['Mã sản phẩm'] == spid) & (lsg['dt'] <= pd.Timestamp('2025-08-09'))].sort_values('dt')
RESULT = r0(float(h['Giá mới'].iloc[-1]))
""",
}.items():
    (OUT/f'{q}.py').write_text(PRE + body)
print('ok')
