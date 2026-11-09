import unicodedata, re, math
tk = BaoCaoTonKho.copy()
m = tk['Tên hàng'].str.lower().str.contains('dau phong rang muoi|đậu phộng rang muối')
RESULT = int(to_num(tk.loc[m, 'Tồn cuối kỳ']).iloc[0])
