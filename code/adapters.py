"""Canonical business adapters for self-generated SFT.

Every business has a different schema.  Instead of writing 30 bespoke solvers,
we map each business to a canonical pair of DataFrames (`orders`, `lines`) plus
optional `products`, `stock`, `purchases`, `payments`, `price_history`,
`customers`.  The generated code is self-contained: it reads the *raw* frames
available to the agent and normalises them, then answers the question.

Canonical columns
-----------------
orders: _oid, _date, _revenue, _bad, _customer, _channel, _payment,
        _paid, _debt, _status
lines : _oid, _date, _product, _category, _qty, _qty_base, _revenue,
        _cost, _unit, _bad, _customer
"""
from __future__ import annotations

import unicodedata


# --------------------------------------------------------------------------
# key resolution (business files use inconsistent unicode normalisation)
# --------------------------------------------------------------------------

def _norm_key(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().replace(" ", "").replace("_", "").replace("-", "")


def resolve_key(data: dict, name: str) -> str:
    """Find the real dataframe key matching a logical name."""
    if name in data:
        return name
    target = _norm_key(name)
    candidates = [k for k in data if not k.startswith("_")]
    for k in candidates:
        if _norm_key(k) == target:
            return k
    for k in candidates:
        if _norm_key(k).startswith(target):
            return k
    for k in candidates:
        if target in _norm_key(k):
            return k
    raise KeyError(f"cannot resolve key {name!r} in {list(data)}")


def _q(s: str) -> str:
    return repr(s)


# --------------------------------------------------------------------------
# prepare-code renderer
# --------------------------------------------------------------------------

def render_prepare(spec: dict) -> str:
    """Render a self-contained code block that builds canonical frames."""
    s = spec
    out = []
    add = out.append

    add("import pandas as pd")
    add("import re as _re")
    add("")
    add("def _frame(name):")
    add("    return globals()[name]")
    add("")
    add("def _flat(x):")
    add("    if isinstance(x, dict):")
    add("        return pd.concat([d for d in x.values() if hasattr(d, 'columns')], ignore_index=True)")
    add("    return x.copy()")
    add("")
    add("def _col(df, name):")
    add("    if name and name in df.columns:")
    add("        return df[name]")
    add("    return pd.Series([None] * len(df), index=df.index)")
    add("")
    add("def _badmask(s):")
    add("    return s.astype(str).str.contains(r'hủy|huỷ|cancel|trả hàng|trả lại|hàng trả về|hoàn trả|hoàn hàng|đổi trả|không giao|thất bại|khach huy|returned', case=False, na=False)")
    add("")
    add("def _cancelmask(s):")
    add("    return s.astype(str).str.contains(r'hủy|huỷ|cancel', case=False, na=False)")
    add("")
    add("def _clean_name(x):")
    add("    s = str(x).strip()")
    add("    s = _re.sub(r'\\s*[-–—(]\\s*0?\\d[\\d\\s.\\-]{7,}\\s*\\)?\\s*$', '', s)")
    add("    s = _re.sub(r'\\s+0?\\d[\\d\\s.\\-]{7,}\\s*$', '', s)")
    add("    return s.strip()")
    add("")
    add("def _money(x):")
    add("    if isinstance(x, (int, float)) and not isinstance(x, bool):")
    add("        return float(x)")
    add("    s = str(x).strip().lower().replace('đ', '').replace(' ', '')")
    add("    if not s or s in ('nan', 'none', ''):")
    add("        return float('nan')")
    add("    m = _re.match(r'^(-?\\d+)[.,](\\d{1,3})tr$', s)")
    add("    if m:")
    add("        return float(m.group(1) + '.' + m.group(2)) * 1000000")
    add("    m = _re.match(r'^(-?\\d+)tr(\\d{3})$', s)")
    add("    if m:")
    add("        return int(m.group(1)) * 1000000 + int(m.group(2)) * 1000")
    add("    mult = 1")
    add("    if s.endswith('tr'):")
    add("        mult, s = 1000000, s[:-2]")
    add("    elif s.endswith('k'):")
    add("        mult, s = 1000, s[:-1]")
    add("    neg = s.startswith('-')")
    add("    s = s.lstrip('-')")
    add("    if ',' in s and '.' in s:")
    add("        if s.rfind(',') > s.rfind('.'):")
    add("            s = s.replace('.', '').replace(',', '.')")
    add("        else:")
    add("            s = s.replace(',', '')")
    add("    elif ',' in s:")
    add("        parts = s.split(',')")
    add("        s = s.replace(',', '') if (len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3)) else s.replace(',', '.')")
    add("    elif '.' in s:")
    add("        parts = s.split('.')")
    add("        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3):")
    add("            s = s.replace('.', '')")
    add("    try:")
    add("        v = float(s) * mult")
    add("    except ValueError:")
    add("        return float('nan')")
    add("    return -v if neg else v")
    add("")

    has_orders = bool(s.get("orders_expr"))

    if has_orders:
        add(f"_o = _flat({s['orders_expr']})")
        add("orders = pd.DataFrame({")
        if s.get("oid"):
            add(f"    '_oid': _col(_o, {_q(s['oid'])}).astype(str),")
        else:
            add("    '_oid': 'R' + pd.RangeIndex(len(_o)).astype(str),")
        add(f"    '_date': parse_date(_col(_o, {_q(s.get('date'))})),")
        add(f"    '_revenue': _col(_o, {_q(s.get('revenue'))}).map(_money),")
        add(f"    '_status': _col(_o, {_q(s.get('status'))}).astype(str),")
        add(f"    '_customer': _col(_o, {_q(s.get('customer'))}).astype(str),")
        if s.get("custcode"):
            add(f"    '_custcode': _col(_o, {_q(s['custcode'])}).astype(str),")
        else:
            add("    '_custcode': '',")
        add(f"    '_channel': _col(_o, {_q(s.get('channel'))}).astype(str),")
        add(f"    '_payment': _col(_o, {_q(s.get('payment'))}).astype(str),")
        add(f"    '_paid': _col(_o, {_q(s.get('paid'))}).map(_money),")
        add(f"    '_debt': _col(_o, {_q(s.get('debt'))}).map(_money),")
        if s.get("total"):
            add(f"    '_total': _col(_o, {_q(s['total'])}).map(_money),")
        else:
            add("    '_total': _col(_o, " + _q(s.get('revenue')) + ").map(_money),")
        if s.get("staff"):
            add(f"    '_staff': _col(_o, {_q(s['staff'])}).astype(str),")
        else:
            add("    '_staff': '',")
        if s.get("timecol"):
            add(f"    '_time': parse_date(_col(_o, {_q(s['timecol'])})),")
        else:
            add("    '_time': pd.NaT,")
        add("})")
        add("orders['_bad'] = _badmask(orders['_status'])")
        add("orders['_cancelled'] = _cancelmask(orders['_status'])")
        add("")

    if s.get("lines_expr"):
        add(f"_l = _flat({s['lines_expr']})")
        if s.get("lines_dedup"):
            add("_l = _l.drop_duplicates()")
        if s.get("drop_na_oid") and s.get("loid"):
            add(f"_l = _l[_l[{_q(s['loid'])}].notna()]")
        if s.get("lffill"):
            _fcols = [s.get("loid"), s.get("ldate"), s.get("status"), s.get("customer")]
            add("for _c in " + repr([c for c in _fcols if c]) + ":")
            add("    if _c in _l.columns:")
            add("        _l[_c] = _l[_c].ffill()")
        add("lines = pd.DataFrame({")
        if s.get("loid"):
            add(f"    '_oid': _col(_l, {_q(s['loid'])}).astype(str),")
        else:
            add("    '_oid': 'R' + pd.RangeIndex(len(_l)).astype(str),")
        add(f"    '_product': _col(_l, {_q(s.get('lproduct'))}).astype(str),")
        if s.get("lkey") and s.get("lkey") != s.get("lproduct"):
            add(f"    '_pkey_val': _col(_l, {_q(s['lkey'])}).astype(str),")
        else:
            add("    '_pkey_val': _col(_l, " + _q(s.get("lproduct")) + ").astype(str),")
        add(f"    '_qty': to_num(_col(_l, {_q(s.get('lqty'))})),")
        qb = s.get("lqty_base") or s.get("lqty")
        add(f"    '_qty_base': to_num(_col(_l, {_q(qb)})),")
        add(f"    '_revenue': _col(_l, {_q(s.get('lrevenue'))}).map(_money),")
        add(f"    '_unit': _col(_l, {_q(s.get('lunit'))}).astype(str),")
        add("    '_staff': '',")
        add("    '_time': pd.NaT,")
        if s.get("lcost"):
            add(f"    '_cost': _col(_l, {_q(s['lcost'])}).map(_money),")
        else:
            add("    '_cost': 0.0,")
        add("})")
        if s.get("ldate"):
            add(f"lines['_date'] = parse_date(_col(_l, {_q(s['ldate'])}))")
        elif has_orders:
            add("_omap = orders.drop_duplicates('_oid').set_index('_oid')")
            add("lines['_date'] = lines['_oid'].map(_omap['_date'])")
        else:
            add("lines['_date'] = pd.NaT")
        if s.get("status") and not has_orders:
            add(f"lines['_bad'] = _badmask(_col(_l, {_q(s['status'])}))")
            add(f"lines['_cancelled'] = _cancelmask(_col(_l, {_q(s['status'])}))")
        elif has_orders:
            add("_omap = orders.drop_duplicates('_oid').set_index('_oid')")
            add("lines['_bad'] = lines['_oid'].map(_omap['_bad']).fillna(False).astype(bool)")
            add("lines['_cancelled'] = lines['_oid'].map(_omap['_cancelled']).fillna(False).astype(bool)")
        else:
            add("lines['_bad'] = False")
            add("lines['_cancelled'] = False")
        if s.get("customer") and not has_orders:
            add(f"lines['_customer'] = _col(_l, {_q(s['customer'])}).astype(str)")
        elif has_orders:
            add("_omap = orders.drop_duplicates('_oid').set_index('_oid')")
            add("lines['_customer'] = lines['_oid'].map(_omap['_customer']).fillna('')")
        else:
            add("lines['_customer'] = ''")
        if has_orders:
            add("lines['_custcode'] = lines['_oid'].map(_omap['_custcode']).fillna('') if '_custcode' in _omap.columns else ''")
        else:
            add("lines['_custcode'] = ''")

        # product key -> name / category mapping
        if s.get("product_expr"):
            add(f"_p = _flat({s['product_expr']})")
            _pcols = [s.get("pkey")]
            _names = ["_pkey"]
            if s.get("pname") and s.get("pname") != s.get("pkey"):
                _pcols.append(s["pname"]); _names.append("_pname")
            if s.get("pcategory"):
                _pcols.append(s["pcategory"]); _names.append("_category")
            add(f"_pmap = _p[{_pcols!r}].drop_duplicates({_q(s.get('pkey'))})")
            add(f"_pmap.columns = {_names!r}")
            add("for _need in ['_pname', '_category']:")
            add("    if _need not in _pmap.columns:")
            add("        _pmap[_need] = ''")
            add("lines = lines.merge(_pmap, left_on='_pkey_val', right_on='_pkey', how='left').drop(columns=['_pkey'])")
            add("_nm = lines['_pname'].astype(str).str.strip()")
            add("lines['_product'] = lines['_product'].where(_nm.isin(['', 'nan', 'None']), lines['_pname'])")
            add("lines = lines.drop(columns=['_pname'])")
            add("lines['_category'] = lines['_category'].fillna('').astype(str)")
            add("_cn = _pmap.copy()")
            if s.get("pname") and s.get("pname") != s.get("pkey"):
                add("_cn['_k'] = _cn['_pname'].map(normalize_text)")
            else:
                add("_cn['_k'] = _cn['_pkey'].map(normalize_text)")
            add("_cn = _cn[_cn['_category'].astype(str).str.strip().ne('')]")
            add("_cn = _cn.drop_duplicates('_k')")
            add("_cmap = _cn.set_index('_k')['_category'].astype(str).to_dict()")
            add("_ckeys = sorted(_cmap, key=len, reverse=True)")
            add("def _cat_of(nm):")
            add("    k = normalize_text(nm)")
            add("    if k in _cmap:")
            add("        return _cmap[k]")
            add("    for _ck in _ckeys:")
            add("        if len(_ck) >= 5 and (_ck in k or k in _ck):")
            add("            return _cmap[_ck]")
            add("    return ''")
            add("_cb = lines['_category'].astype(str).str.strip().eq('')")
            add("if _cb.any():")
            add("    lines.loc[_cb, '_category'] = lines.loc[_cb, '_product'].map(_cat_of)")
        else:
            add("lines['_category'] = ''")
        add("")

        if not has_orders:
            add("orders = lines.groupby('_oid', as_index=False).agg(")
            add("    _date=('_date', 'min'), _revenue=('_revenue', 'sum'),")
            add("    _bad=('_bad', 'max'), _cancelled=('_cancelled', 'max'), _customer=('_customer', 'first'))")
            add("orders['_status'] = orders['_bad'].map({True: 'cancelled', False: 'completed'})")
            add("orders['_channel'] = ''")
            add("orders['_payment'] = ''")
            add("orders['_paid'] = orders['_revenue']")
            add("orders['_debt'] = 0.0")
            add("orders['_staff'] = ''")
            add("orders['_total'] = orders['_revenue']")
            add("orders['_time'] = orders['_date']")
            add("")
    else:
        add("lines = pd.DataFrame(columns=['_oid', '_date', '_product', '_category', '_qty', '_qty_base', '_revenue', '_cost', '_unit', '_bad', '_cancelled', '_customer'])")
        add("")

    # products
    if s.get("product_expr"):
        add(f"_p = _flat({s['product_expr']})")
        add("products = pd.DataFrame({")
        add(f"    '_pkey': _col(_p, {_q(s.get('pkey'))}).astype(str),")
        add(f"    '_product': _col(_p, {_q(s.get('pname') or s.get('pkey'))}).astype(str),")
        if s.get("pcategory"):
            add(f"    '_category': _col(_p, {_q(s['pcategory'])}).astype(str),")
        else:
            add("    '_category': '',")
        if s.get("pprice"):
            add(f"    '_price': _col(_p, {_q(s['pprice'])}).map(_money),")
        else:
            add("    '_price': 0.0,")
        if s.get("pcost"):
            add(f"    '_cost': _col(_p, {_q(s['pcost'])}).map(_money),")
        else:
            add("    '_cost': 0.0,")
        if s.get("pingr"):
            add(f"    '_ingredient': _col(_p, {_q(s['pingr'])}).astype(str),")
        else:
            add("    '_ingredient': '',")
        add("})")
        add("")
    else:
        add("products = pd.DataFrame(columns=['_pkey', '_product', '_category', '_price', '_cost', '_ingredient'])")
        add("")

    # ingredient catalog (medicine -> active ingredient) keyed by product code
    if s.get("ingr_expr"):
        add(f"_ig = _flat({s['ingr_expr']})")
        add(f"_imap = pd.Series(_col(_ig, {_q(s.get('ingrname'))}).astype(str).replace({{'None': '', 'nan': ''}}).values, index=_col(_ig, {_q(s.get('ingrkey'))}).astype(str).values)")
        add("_imap = _imap[~_imap.index.duplicated(keep='first')].to_dict()")
        add("products['_ingredient'] = products.apply(lambda r: _imap.get(str(r['_pkey']), r['_ingredient']), axis=1).astype(str)")
        add("")
    else:
        add("_imap = {}")
        add("")

    # prescription catalog
    if s.get("rx_expr"):
        add(f"_rx = _flat({s['rx_expr']})")
        add(f"_rxraw = _col(_rx, {_q(s.get('rxflag'))}).astype(str)")
        add("_rxval = _rxraw.str.lower().str.contains(r'1|true|yes|có|co|kê|ke|x', regex=True, na=False)")
        add(f"_rxmap = pd.Series(_rxval.values, index=_col(_rx, {_q(s.get('rxkey'))}).astype(str).values)")
        add("_rxmap = _rxmap[~_rxmap.index.duplicated(keep='first')].to_dict()")
        add("products['_rx'] = products['_pkey'].map(lambda x: bool(_rxmap.get(str(x), False)))")
        add("")
    else:
        add("_rxmap = {}")
        add("products['_rx'] = False")
        add("")

    # SKU -> display name mapping (purchase/lot tables often store only SKUs)
    if s.get("sku_expr"):
        add(f"_sk = _flat({s['sku_expr']})")
        add(f"_skumap = pd.Series(_col(_sk, {_q(s.get('skuname'))}).astype(str).values, index=_col(_sk, {_q(s.get('skukey'))}).astype(str).values)")
        add("_skumap = _skumap[~_skumap.index.duplicated(keep='first')].to_dict()")
        add("")
    else:
        add("_skumap = {}")
        add("")
    add("_imap_named = {}")
    add("if _skumap and _imap:")
    add("    _imap_named = { _skumap.get(str(k), str(k)): v for k, v in _imap.items() }")
    add("_rx_named = {}")
    add("if _skumap and _rxmap:")
    add("    _rx_named = { _skumap.get(str(k), str(k)): v for k, v in _rxmap.items() }")
    add("")

    # stock
    if s.get("stock_expr"):
        add(f"_s = _flat({s['stock_expr']})")
        if s.get("sdate"):
            add(f"_s = _s.assign(_sdt=parse_date(_col(_s, {_q(s['sdate'])})))")
            add("_s = _s.sort_values('_sdt')")
            add(f"_s = _s.drop_duplicates(subset=[{_q(s.get('sname'))}], keep='last')")
        add("stock = pd.DataFrame({")
        add(f"    '_product': _col(_s, {_q(s.get('sname'))}).astype(str),")
        add(f"    '_stock': to_num(_col(_s, {_q(s.get('sqty'))})),")
        add("})")
        add("")
    else:
        add("stock = pd.DataFrame(columns=['_product', '_stock'])")
        add("")

    # deliveries
    if s.get("deliv_expr"):
        add(f"_dv = _flat({s['deliv_expr']})")
        add("deliveries = pd.DataFrame({")
        add(f"    '_date': parse_date(_col(_dv, {_q(s.get('ddate'))})),")
        add(f"    '_oid': _col(_dv, {_q(s.get('doid'))}).astype(str),")
        add(f"    '_line': _col(_dv, {_q(s.get('dline'))}).astype(str),")
        add(f"    '_qty': to_num(_col(_dv, {_q(s.get('dqty'))})),")
        add("})")
        add("")
    else:
        add("deliveries = pd.DataFrame(columns=['_date', '_oid', '_line', '_qty'])")
        add("")

    # purchases (header-level: one row per purchase order)
    if s.get("purch_expr"):
        add(f"_pu = _flat({s['purch_expr']})")
        add("purchases = pd.DataFrame({")
        add(f"    '_oid': _col(_pu, {_q(s.get('puoid'))}).astype(str),")
        add(f"    '_date': parse_date(_col(_pu, {_q(s.get('pudate'))})),")
        add(f"    '_product': _col(_pu, {_q(s.get('puproduct'))}).astype(str),")
        add(f"    '_qty': to_num(_col(_pu, {_q(s.get('puqty'))})),")
        if s.get("puamount"):
            add(f"    '_amount': _col(_pu, {_q(s['puamount'])}).map(_money),")
        else:
            add("    '_amount': float('nan'),")
        if s.get("pusupplier"):
            add(f"    '_supplier': _col(_pu, {_q(s['pusupplier'])}).astype(str),")
        else:
            add("    '_supplier': '',")
        if s.get("pustatus"):
            add(f"    '_bad': _badmask(_col(_pu, {_q(s['pustatus'])})),")
        else:
            add("    '_bad': False,")
        add("})")
        add("")
    else:
        add("purchases = pd.DataFrame(columns=['_oid', '_date', '_product', '_qty', '_amount', '_supplier', '_bad'])")
        add("")

    # purchase detail lines (product-level, price)
    if s.get("pud_expr"):
        add(f"_pud = _flat({s['pud_expr']})")
        add("purchase_lines = pd.DataFrame({")
        add(f"    '_oid': _col(_pud, {_q(s.get('pudoid'))}).astype(str),")
        if s.get("puddate"):
            add(f"    '_date': parse_date(_col(_pud, {_q(s['puddate'])})),")
        else:
            add("    '_date': pd.NaT,")
        add(f"    '_product': _col(_pud, {_q(s.get('pudproduct'))}).astype(str),")
        add(f"    '_qty': to_num(_col(_pud, {_q(s.get('pudqty'))})),")
        if s.get("pudprice"):
            add(f"    '_price': _col(_pud, {_q(s['pudprice'])}).map(_money),")
        else:
            add("    '_price': float('nan'),")
        add(f"    '_unit': _col(_pud, {_q(s.get('pudunit'))}).astype(str),")
        add("})")
        if not s.get("puddate"):
            add("_pdm = purchases.drop_duplicates('_oid').set_index('_oid')['_date'].to_dict() if len(purchases) else {}")
            add("purchase_lines['_date'] = purchase_lines['_oid'].map(lambda x: _pdm.get(str(x), pd.NaT))")
        add("purchase_lines['_amount'] = purchase_lines['_qty'] * purchase_lines['_price']")
        add("")
    else:
        add("purchase_lines = pd.DataFrame(columns=['_oid', '_date', '_product', '_qty', '_price', '_unit', '_amount'])")
        add("")

    # stock transactions (running balance) for stock-at-date
    if s.get("stockt_expr"):
        add(f"_st = _flat({s['stockt_expr']})")
        add("stock_tx = pd.DataFrame({")
        add(f"    '_product': _col(_st, {_q(s.get('stocktproduct'))}).astype(str),")
        add(f"    '_date': parse_date(_col(_st, {_q(s.get('stocktdate'))})),")
        add(f"    '_qty': to_num(_col(_st, {_q(s.get('stocktqty'))})),")
        if s.get("stocktbalance"):
            add(f"    '_balance': to_num(_col(_st, {_q(s['stocktbalance'])})),")
        else:
            add("    '_balance': float('nan'),")
        add("})")
        add("")
    else:
        add("stock_tx = pd.DataFrame(columns=['_product', '_date', '_qty', '_balance'])")
        add("")

    # lots (expiry / remaining quantity)
    if s.get("lot_expr"):
        add(f"_lt = _flat({s['lot_expr']})")
        add("lots = pd.DataFrame({")
        add(f"    '_lot': _col(_lt, {_q(s.get('lotid'))}).astype(str),")
        add(f"    '_product': _col(_lt, {_q(s.get('lotproduct'))}).astype(str),")
        add(f"    '_expiry': parse_date(_col(_lt, {_q(s.get('lotexpiry'))})),")
        add(f"    '_qty': to_num(_col(_lt, {_q(s.get('lotqty'))})),")
        if s.get("lotprice"):
            add(f"    '_price': _col(_lt, {_q(s['lotprice'])}).map(_money),")
        else:
            add("    '_price': float('nan'),")
        if s.get("lotpurch"):
            add(f"    '_purch': _col(_lt, {_q(s['lotpurch'])}).astype(str),")
        else:
            add("    '_purch': '',")
        add("})")
        if s.get("lotpurch"):
            add("_pdmap = purchases.drop_duplicates('_oid').set_index('_oid')['_date'].to_dict() if len(purchases) else {}")
            add("lots['_date'] = lots['_purch'].map(lambda x: _pdmap.get(str(x), pd.NaT))")
        else:
            add("lots['_date'] = pd.NaT")
        add("")
    else:
        add("lots = pd.DataFrame(columns=['_lot', '_product', '_expiry', '_qty', '_price'])")
        add("")

    if s.get("lotsold_expr"):
        add(f"_ls = _flat({s['lotsold_expr']})")
        add("lot_sales = pd.DataFrame({")
        add(f"    '_lot': _col(_ls, {_q(s.get('lotsoldlot'))}).astype(str),")
        add(f"    '_oid': _col(_ls, {_q(s.get('lotsoldoid'))}).astype(str),")
        if s.get("lotsolddate"):
            add(f"    '_date': parse_date(_col(_ls, {_q(s['lotsolddate'])})),")
        else:
            add("    '_date': pd.NaT,")
        add(f"    '_qty': to_num(_col(_ls, {_q(s.get('lotsoldqty'))})),")
        if s.get("lotsoldret"):
            add(f"    '_ret': to_num(_col(_ls, {_q(s['lotsoldret'])})),")
        else:
            add("    '_ret': 0.0,")
        add("})")
        if not s.get("lotsolddate"):
            add("_lsd = orders.drop_duplicates('_oid').set_index('_oid')['_date'].to_dict() if len(orders) else {}")
            add("lot_sales['_date'] = lot_sales['_oid'].map(lambda x: _lsd.get(str(x), pd.NaT))")
        add("lot_sales['_qty'] = lot_sales['_qty'] - lot_sales['_ret']")
        add("")
    else:
        add("lot_sales = pd.DataFrame(columns=['_lot', '_oid', '_date', '_qty'])")
        add("")

    # unit conversions (large unit -> base units)
    if s.get("conv_expr"):
        add(f"_cv = _flat({s['conv_expr']})")
        add("conversions = pd.DataFrame({")
        add(f"    '_pkey': _col(_cv, {_q(s.get('convkey'))}).astype(str),")
        add(f"    '_unit': _col(_cv, {_q(s.get('convunit'))}).astype(str),")
        add(f"    '_ratio': to_num(_col(_cv, {_q(s.get('convratio'))})),")
        add("})")
        add("")
    else:
        add("conversions = pd.DataFrame(columns=['_pkey', '_unit', '_ratio'])")
        add("")

    # payments
    if s.get("pay_expr"):
        add(f"_pay = _flat({s['pay_expr']})")
        add("payments = pd.DataFrame({")
        add(f"    '_oid': _col(_pay, {_q(s.get('payoid'))}).astype(str),")
        add(f"    '_date': parse_date(_col(_pay, {_q(s.get('paydate'))})),")
        add(f"    '_amount': _col(_pay, {_q(s.get('payamount'))}).map(_money),")
        if s.get("paymethod"):
            add(f"    '_method': _col(_pay, {_q(s['paymethod'])}).astype(str),")
        else:
            add("    '_method': '',")
        add("})")
        add("")
    else:
        add("payments = pd.DataFrame(columns=['_oid', '_date', '_amount', '_method'])")
        add("")

    # price history
    if s.get("ph_expr"):
        add(f"_ph = _flat({s['ph_expr']})")
        add("price_history = pd.DataFrame({")
        add(f"    '_product': _col(_ph, {_q(s.get('phproduct'))}).astype(str),")
        add(f"    '_date': parse_date(_col(_ph, {_q(s.get('phdate'))})),")
        add(f"    '_new_price': _col(_ph, {_q(s.get('phnew'))}).map(_money),")
        if s.get("phold"):
            add(f"    '_old_price': _col(_ph, {_q(s['phold'])}).map(_money),")
        else:
            add("    '_old_price': float('nan'),")
        add("})")
        add("")
    else:
        add("price_history = pd.DataFrame(columns=['_product', '_date', '_new_price', '_old_price'])")
        add("")

    # customers
    if s.get("cust_expr"):
        add(f"_cu = _flat({s['cust_expr']})")
        add("customers = pd.DataFrame({")
        add(f"    '_cid': _col(_cu, {_q(s.get('custid'))}).astype(str),")
        add(f"    '_cname': _col(_cu, {_q(s.get('custname'))}).astype(str).map(_clean_name),")
        if s.get("custtier"):
            add(f"    '_tier': _col(_cu, {_q(s['custtier'])}).astype(str),")
        else:
            add("    '_tier': '',")
        if s.get("custbirth"):
            add(f"    '_birthday': parse_date(_col(_cu, {_q(s['custbirth'])})),")
        else:
            add("    '_birthday': pd.NaT,")
        add("})")
        add("")
    else:
        add("customers = pd.DataFrame(columns=['_cid', '_cname', '_tier', '_birthday'])")
        add("")

    # staff catalog (employee code -> name)
    if s.get("staff_expr"):
        add(f"_st = _flat({s['staff_expr']})")
        add("staff = pd.DataFrame({")
        add(f"    '_sid': _col(_st, {_q(s.get('staffkey'))}).astype(str),")
        add(f"    '_sname': _col(_st, {_q(s.get('staffname'))}).astype(str),")
        add("})")
        add("")
    else:
        add("staff = pd.DataFrame(columns=['_sid', '_sname'])")
        add("")

    # ---- derived dimensions ----
    add("def _shift_of(dt):")
    add("    dt = pd.to_datetime(dt, errors='coerce')")
    add("    _h = dt.dt.hour")
    add("    _out = pd.Series('', index=dt.index, dtype=object)")
    add("    _out[(_h >= 6) & (_h <= 13)] = 'sang'")
    add("    _out[(_h >= 14) & (_h <= 21)] = 'chieu'")
    add("    return _out")
    add("")
    add("if len(orders):")
    add("    _tm = orders.drop_duplicates('_oid').set_index('_oid')['_time'].to_dict()")
    add("    lines['_time'] = lines['_oid'].map(lambda x: _tm.get(str(x), pd.NaT))")
    add("lines['_time'] = pd.to_datetime(lines['_time'], errors='coerce').fillna(lines['_date'])")
    add("orders['_time'] = pd.to_datetime(orders['_time'], errors='coerce').fillna(orders['_date'])")
    add("for _df in (orders, lines):")
    add("    _df['_shift'] = _shift_of(_df['_time'])")
    add("")
    add("def _size_of(x):")
    add("    s = str(x).upper()")
    add("    m = _re.search(r'\\(\\s*([ML])\\s*\\)', s)")
    add("    if m:")
    add("        return m.group(1).lower()")
    add("    m = _re.search(r'\\bSIZE\\s*([ML])\\b', s)")
    add("    if m:")
    add("        return m.group(1).lower()")
    add("    return ''")
    add("")
    add("lines['_size'] = lines['_product'].map(_size_of)")
    add("")
    add("if len(orders):")
    add("    _sm = orders.drop_duplicates('_oid').set_index('_oid')['_staff'].to_dict()")
    add("    lines['_staff'] = lines['_oid'].map(lambda x: _sm.get(str(x), '')).fillna('').astype(str)")
    add("    for _c in ('_payment', '_channel'):")
    add("        _mp = orders.drop_duplicates('_oid').set_index('_oid')[_c].to_dict()")
    add("        lines[_c] = lines['_oid'].map(lambda x: _mp.get(str(x), '')).fillna('').astype(str)")
    add("else:")
    add("    lines['_payment'] = ''")
    add("    lines['_channel'] = ''")
    add("")
    add("if len(staff):")
    add("    _sn = staff.drop_duplicates('_sid').set_index('_sid')['_sname'].to_dict()")
    add("    for _df in (orders, lines):")
    add("        _df['_staff_name'] = _df['_staff'].map(lambda x: _sn.get(str(x), '')).fillna('').astype(str)")
    add("else:")
    add("    for _df in (orders, lines):")
    add("        _df['_staff_name'] = ''")
    add("")
    add("if len(customers):")
    add("    _c1 = customers.drop_duplicates('_cid').set_index('_cid')['_tier'].astype(str).to_dict()")
    add("    def _cnorm(x):")
    add("        t = str(x)")
    add("        t = _re.sub(r'\\s*\\([^)]*\\)\\s*$', '', t)")
    add("        t = _re.sub(r'\\s*-?\\s*\\d[\\d\\s\\.]{7,}$', '', t)")
    add("        return normalize_text(t)")
    add("    _c2 = customers.assign(_k=customers['_cname'].map(_cnorm)).drop_duplicates('_k').set_index('_k')['_tier'].astype(str).to_dict()")
    add("    def _tier_of(x):")
    add("        k = str(x).strip()")
    add("        return _c1.get(k) or _c2.get(_cnorm(x)) or ''")
    add("    def _tier_row(x, code=''):")
    add("        k = str(x).strip()")
    add("        return _c1.get(str(code).strip(), '') or _c1.get(k) or _c2.get(_cnorm(x)) or ''")
    add("    orders['_tier'] = [ _tier_row(a, b) for a, b in zip(orders['_customer'], orders.get('_custcode', pd.Series([''] * len(orders)))) ]")
    add("    lines['_tier'] = [ _tier_row(a, b) for a, b in zip(lines['_customer'], lines.get('_custcode', pd.Series([''] * len(lines)))) ]")
    add("else:")
    add("    orders['_tier'] = ''")
    add("    lines['_tier'] = ''")
    add("")
    add("_pkey2name = products.drop_duplicates('_pkey').set_index('_pkey')['_product'].to_dict() if len(products) else {}")
    add("_pname2key = products.drop_duplicates('_product').set_index('_product')['_pkey'].to_dict() if len(products) else {}")
    add("def _disp(x):")
    add("    return _skumap.get(str(x)) or _pkey2name.get(str(x)) or str(x)")
    add("if len(stock):")
    add("    stock['_product'] = stock['_product'].map(_disp)")
    add("if len(purchase_lines):")
    add("    purchase_lines['_pname'] = purchase_lines['_product'].map(_disp)")
    add("if len(lots):")
    add("    lots['_pname'] = lots['_product'].map(_disp)")
    add("if len(stock_tx):")
    add("    stock_tx['_pname'] = stock_tx['_product'].map(_disp)")
    add("if len(conversions):")
    add("    conversions['_pname'] = conversions['_pkey'].map(_disp)")
    add("if len(price_history):")
    add("    price_history['_pname'] = price_history['_product'].map(_disp)")
    if s.get("conv_expr") and not s.get("lqty_base"):
        # no explicit base-qty column: derive it from the unit conversion table
        add("if len(conversions) and len(lines):")
        add("    _cratio = conversions.assign(_k=conversions['_pname'].map(normalize_text), _u=conversions['_unit'].map(normalize_text)).drop_duplicates(['_k', '_u']).set_index(['_k', '_u'])['_ratio'].to_dict()")
        add("    _lk = lines['_product'].map(normalize_text)")
        add("    _lu = lines['_unit'].map(normalize_text)")
        add("    _rr = [ _cratio.get((k, u), 1.0) for k, u in zip(_lk, _lu) ]")
        add("    lines['_qty_base'] = [ (q * r) if (r == r and r and r > 0) else q for q, r in zip(lines['_qty'], _rr) ]")
    add("if len(lot_sales):")
    add("    _lotprod = lots.drop_duplicates('_lot').set_index('_lot')['_product'].to_dict() if len(lots) else {}")
    add("    lot_sales['_product'] = lot_sales['_lot'].map(lambda x: _disp(_lotprod.get(str(x), '')))")
    add("")
    add("_i1 = products.drop_duplicates('_pkey').set_index('_pkey')['_ingredient'].astype(str).to_dict() if len(products) else {}")
    add("_i2 = products.drop_duplicates('_product').set_index('_product')['_ingredient'].astype(str).to_dict() if len(products) else {}")
    add("_i2.update(_imap_named)")
    add("_i3 = {}")
    add("if len(products):")
    add("    _i3 = products.assign(_k=products['_product'].map(normalize_text)).drop_duplicates('_k').set_index('_k')['_ingredient'].astype(str).to_dict()")
    add("def _ingr_of(r):")
    add("    v = _i1.get(str(r['_pkey_val']), '') or _i2.get(str(r['_product']), '') or _i2.get(str(r['_pkey_val']), '') or _i3.get(normalize_text(r['_product']), '')")
    add("    return '' if str(v) in ('None', 'nan') else str(v)")
    add("lines['_ingredient'] = lines.apply(_ingr_of, axis=1) if (len(_i1) or len(_i2)) else ''")
    add("_k_ingr = lines.assign(_k=lines['_product'].map(normalize_text))")
    add("_k_ingr = _k_ingr[_k_ingr['_ingredient'].astype(str).str.strip().ne('') & _k_ingr['_ingredient'].astype(str).ne('nan')]")
    add("_k_ingr = _k_ingr.drop_duplicates('_k').set_index('_k')['_ingredient'].to_dict()")
    add("lines['_ingredient'] = [ (str(v) if str(v).strip() not in ('', 'None', 'nan') else _k_ingr.get(normalize_text(pp), '')) for pp, v in zip(lines['_product'], lines['_ingredient']) ]")
    add("")
    add("_r1 = products.drop_duplicates('_pkey').set_index('_pkey')['_rx'].to_dict() if len(products) else {}")
    add("_r2 = products.drop_duplicates('_product').set_index('_product')['_rx'].to_dict() if len(products) else {}")
    add("_r2.update(_rx_named)")
    add("def _rx_of(r):")
    add("    return bool(_r1.get(str(r['_pkey_val']), False) or _r2.get(str(r['_product']), False))")
    add("lines['_rx'] = lines.apply(_rx_of, axis=1) if (len(_r1) or len(_r2)) else False")
    add("orders['_rx'] = False")
    add("_rxo = lines.groupby('_oid')['_rx'].max().to_dict()")
    add("orders['_rx'] = orders['_oid'].map(lambda x: bool(_rxo.get(str(x), False)))")
    add("")

    return "\n".join(out)


# --------------------------------------------------------------------------
# business specs
# --------------------------------------------------------------------------

_SPECS_RAW = {
    # ---------------- flat ban_hang ----------------
    "biz_101": dict(
        sales="ban_hang", oid="Mã hóa đơn", date="Ngày tháng", revenue="Thanh tien",
        status="Kết quả", customer="Đối tác", product="Nội dung",
        qty="so_luong", qty_base="Quy ra ĐV lẻ", unit="Đơn vị (tính)",
    ),
    "biz_114": dict(
        sales="ban_hang", oid="Mã GD", date="Ngày", revenue="Tổng",
        status="trang_thai", customer="Tên khách", product="Sản phẩm",
        qty="Sluong", qty_base="Quy ra ĐV lẻ", unit="Đơn vị tính",
    ),
    "biz_125": dict(
        sales="ban_hang", oid="Số phiếu", date="Ngày bán", revenue="Amount",
        status="Trạng thái xử lý", customer="Khách hàng (tên)", product="Hàng bán",
        qty="SL bán", qty_base="Số lượng lẻ", unit="dvt",
    ),
    "biz_126": dict(
        sales="SoBanHang", oid=None, date="Ngày tháng", revenue="Thành tiền (đ)",
        status="Trạng thái đơn", product="Ten hang",
        qty="Số lượng bán", qty_base="SL lẻ", unit="Đơn vị tính",
    ),
    "biz_107": dict(
        sales="SoBanHang", oid=None, date="ngay_ban", revenue="Tổng tiền",
        status="Trạng thái xử lý", product="Nội dung",
        qty="Số lượng", qty_base="Số lượng lẻ", unit="Đơn vị (tính)",
    ),
    "biz_113": dict(
        sales="SoBanHang", oid=None, date="Ngày mua", revenue="thanh_tien",
        status="Ghi chú TT", product="Mặt hàng",
        qty="SL bán", qty_base="Số lượng lẻ", unit="DonVi",
    ),
    "biz_105": dict(
        sales=["SoBanHang_1", "SoBanHang_2026"], oid="Mã hóa đơn", date="Giờ",
        revenue="Trị giá", status="Status", customer="Khách", product="Hàng",
        qty="so_luong", qty_base=None, unit="Unit",
        purch="SoNhapHang", pudate="Ngày nhập", puproduct="Tên mặt hàng",
        puqty="SL nhập", puamount="Thành tiền", pusupplier="Nhà cung cấp",
        stock="TonKho", sname="Hàng hóa", sqty="Tồn cuối",
        ph="BangGia", phproduct="ten_hang", phdate="Ngày áp dụng",
        phnew="Giá mới", phold="Giá cũ",
    ),
    "biz_117": dict(
        sales="SoBanHang", oid="Mã phiếu", date="Giờ", revenue="Tiền",
        lines_dedup=True,
        status="Ghi chú TT", customer="TenKH", product="Tên SP",
        qty="Số lượng hàng", qty_base=None, unit="DonVi",
        purch="SoNhapHang", pudate="Ngày nhập", puproduct="Product",
        puqty="SL nhập", puamount="Thành tiền", pusupplier="Nhà cung cấp",
        stock="TonKho", sname="Product", sqty="Tồn thực",
        ph="BangGia", phproduct="TenHang", phdate="Ngày áp dụng",
        phnew="Giá mới", phold="Giá cũ",
        deliv="SoGiaoHang", ddate="Ngày chở", doid="Mã bill",
        dline="Lượt giao", dqty="SL thực giao",
    ),
    # ---------------- flat So_chi_tiet_ban_hang ----------------
    "biz_112": dict(
        sales=["So_chi_tiet_ban_hang_1", "So_chi_tiet_ban_hang_2026"],
        oid="Mã đơn hàng", date="Ngày", revenue="Thành tiền", status="Trạng thái",
        product="Tên hàng hóa", qty="Số lượng", qty_base="Số lượng quy đổi",
        unit="Đơn vị tính",
        product_expr="Danh sách hàng hóa", pkey="Tên hàng hóa",
        pcategory="Nhóm hàng hóa", pname="Tên hàng hóa", pprice="Giá bán", pcost="Giá vốn",
    ),
    "biz_115": dict(
        sales="So_chi_tiet_ban_hang", oid="Mã đơn hàng", date="Ngày",
        deliv="Bảng kê phiếu giao hàng", ddate="Ngày giao hàng", doid="Mã đơn hàng",
        dline="Lần giao", dqty="Số lượng giao",
        revenue="Thành tiền", status="Trạng thái", customer="Khách hàng",
        product="Tên hàng hóa", qty="Số lượng", qty_base="Số lượng quy đổi",
        unit="Đơn vị tính",
        product_expr="Danh sách hàng hóa", pkey="Tên hàng hóa",
        pcategory="Nhóm hàng hóa", pname="Tên hàng hóa", pcost="Giá vốn",
    ),
    "biz_118": dict(
        sales="So_chi_tiet_ban_hang", oid="Mã đơn hàng", date="Ngày",
        deliv="Bảng kê phiếu giao hàng", ddate="Ngày giao hàng", doid="Mã đơn hàng",
        dline="Lần giao", dqty="Số lượng giao",
        revenue="Thành tiền", status="Trạng thái", customer="Khách hàng",
        product="Tên hàng hóa", qty="Số lượng", qty_base="Số lượng quy đổi",
        unit="Đơn vị tính",
        product_expr="Danh sách hàng hóa", pkey="Tên hàng hóa",
        pcategory="Nhóm hàng hóa", pname="Tên hàng hóa", pcost="Giá vốn",
    ),
    "biz_116": dict(
        sales=("Bao_cao_ban_hang", "So_chi_tiet_ban_hang"), oid="Mã đơn hàng",
        date="Ngày", revenue="Thành tiền", status="Trạng thái",
        customer="Khách hàng", product="Tên hàng hóa", qty="Số lượng",
        qty_base="Số lượng quy đổi", unit="Đơn vị tính",
        product_expr=("Bao_cao_ban_hang", "Danh sách hàng hóa"), pkey="Tên hàng hóa",
        pcategory="Nhóm hàng hóa", pname="Tên hàng hóa", pcost="Giá vốn",
    ),
    "biz_130": dict(
        sales=["So_chi_tiet_ban_hang_1", "So_chi_tiet_ban_hang_2"],
        oid="Mã đơn hàng", date="Ngày", revenue="Thành tiền", status="Trạng thái",
        product="Tên hàng hóa", qty="Số lượng", qty_base="Số lượng quy đổi",
        unit="Đơn vị tính",
        product_expr="Danh sách hàng hóa", pkey="Tên hàng hóa",
        pcategory="Nhóm hàng hóa", pname="Tên hàng hóa", pcost="Giá vốn",
    ),
    # ---------------- DonHang_ChiTiet ----------------
    "biz_102": dict(
        lines="DonHang_ChiTiet", loid="Mã đơn hàng", ldate="Ngày đặt hàng",
        lproduct="Tên sản phẩm", lqty="Số lượng sản phẩm", lrevenue="Tổng tiền",
        lunit="Đơn vị tính", status="Trạng thái đơn hàng", customer="Tên khách hàng",
    ),
    "biz_103": dict(
        lines="DonHang_ChiTiet", loid="Mã đơn hàng", ldate="Ngày đặt hàng",
        lproduct="Tên sản phẩm", lqty="Số lượng sản phẩm", lrevenue="Tổng tiền",
        lunit="Đơn vị tính", status="Trạng thái đơn hàng", customer="Tên khách hàng",
        lffill=True,
    ),
    "biz_104": dict(
        lines="DonHang_ChiTiet", loid="Mã đơn hàng", ldate="Ngày đặt hàng",
        lproduct="Tên sản phẩm", lqty="Số lượng sản phẩm", lrevenue="Tổng tiền",
        lunit="Đơn vị tính", status="Trạng thái đơn hàng", customer="Tên khách hàng",
        drop_na_oid=True,
    ),
    "biz_121": dict(
        lines="DonHang_ChiTiet", loid="Mã đơn hàng", ldate="Ngày đặt hàng",
        lproduct="Tên sản phẩm", lqty="Số lượng sản phẩm", lrevenue="Tổng tiền",
        lunit="Đơn vị tính", status="Trạng thái đơn hàng", customer="Tên khách hàng",
        lffill=True,
    ),
    "biz_122": dict(
        lines=["DonHang_ChiTiet_1", "DonHang_ChiTiet_2026"], loid="Mã đơn hàng",
        ldate="Ngày đặt hàng", lproduct="Tên sản phẩm", lqty="Số lượng sản phẩm",
        lrevenue="Tổng tiền", lunit="Đơn vị tính",
        status="Trạng thái đơn hàng", customer="Tên khách hàng",
        lffill=True,
        product_expr="DanhSachSanPham", pkey="Tên sản phẩm",
        pcategory="Loại sản phẩm", pname="Tên sản phẩm",
    ),
    # ---------------- DanhSachHoaDon + details ----------------
    "biz_106": dict(
        orders="DanhSachHoaDon", oid="Mã hóa đơn", date="Thời gian",
        revenue="Tổng tiền hàng", total="Tổng sau giảm giá",
        status="Trạng thái", customer="Khách hàng", custcode="Mã KH",
        payment="Phương thức thanh toán", paid="Khách đã trả", debt="Còn nợ",
        timecol="Thời gian tạo",
        cust_expr="DanhSachKhachHang", custid="Mã khách hàng",
        custname="Tên khách hàng", custphone="Điện thoại",
        lines=["DanhSachHoaDonChiTiet_1", "DanhSachHoaDonChiTiet_2"],
        lines_dedup=True, loid="Mã hóa đơn", lproduct="Tên hàng",
        lkey="Mã hàng",
        lqty="Số lượng", lqty_base="Số lượng quy đổi", lrevenue="Thành tiền",
        lunit="Đơn vị tính", lcost="Giá vốn",
        product_expr="DanhSachSanPham", pkey="Mã hàng", pname="Tên hàng",
        pcategory="Nhóm hàng(3 Cấp)", pprice="Giá bán", pcost="Giá vốn",
        stock="BaoCaoTonKho", sname="Tên hàng", sqty="Tồn cuối kỳ",
    ),
    "biz_108": dict(
        orders="DanhSachHoaDon", oid="Mã hóa đơn", date="Thời gian",
        revenue="Tổng tiền hàng", total="Tổng sau giảm giá",
        status="Trạng thái", customer="Khách hàng",
        channel="Kênh bán", paid="Khách đã trả", debt="Còn nợ",
        staff="Người bán", timecol="Thời gian tạo",
        cust_expr="DanhSachKhachHang", custid="Mã khách hàng",
        custcode="Mã KH",
        custname="Tên khách hàng", custtier="Nhóm khách hàng",
        lines="DanhSachHoaDonChiTiet", loid="Mã hóa đơn", lproduct="Tên hàng",
        lkey="Mã hàng",
        lqty="Số lượng", lqty_base="Số lượng quy đổi", lrevenue="Thành tiền",
        lunit="Đơn vị tính",
        product_expr="DanhSachSanPham", pkey="Mã hàng", pname="Tên hàng",
        pcategory="Nhóm hàng(3 Cấp)", pprice="Giá bán",
        stock="BaoCaoTonKho", sname="Tên hàng", sqty="Tồn cuối kỳ",
    ),
    "biz_119": dict(
        orders="DanhSachHoaDon", oid="Mã hóa đơn", date="Thời gian",
        revenue="Tổng tiền hàng", status="Trạng thái", customer="Khách hàng",
        paid="Khách đã trả", debt="Còn nợ",
        lines="DanhSachHoaDonChiTiet", loid="Mã hóa đơn", lproduct="Tên hàng",
        lkey="Mã hàng",
        lqty="Số lượng", lqty_base="Số lượng quy đổi", lrevenue="Thành tiền",
        lines_dedup=True,
        product_expr="DanhSachSanPham", pkey="Mã hàng", pname="Tên hàng",
        pcategory="Nhóm hàng(3 Cấp)", pprice="Giá bán",
        stock="BaoCaoTonKho", sname="Tên hàng", sqty="Tồn cuối kỳ",
    ),
    "biz_120": dict(
        orders="DanhSachHoaDon", oid="Mã hóa đơn", date="Thời gian",
        revenue="Tổng tiền hàng", status="Trạng thái", customer="Khách hàng",
        paid="Khách đã trả", debt="Còn nợ",
        lines="DanhSachHoaDonChiTiet", loid="Mã hóa đơn", lproduct="Tên hàng",
        lkey="Mã hàng",
        lqty="Số lượng", lqty_base="Số lượng quy đổi", lrevenue="Thành tiền",
        product_expr="DanhSachSanPham", pkey="Mã hàng", pname="Tên hàng",
        pcategory="Nhóm hàng(3 Cấp)", pprice="Giá bán", pcost="Giá vốn",
        stock="BaoCaoTonKho", sname="Tên hàng", sqty="Tồn cuối kỳ",
    ),
    "biz_128": dict(
        orders="DanhSachHoaDon", oid="Mã hóa đơn", date="Thời gian",
        revenue="Tổng tiền hàng", status="Trạng thái", customer="Khách hàng",
        paid="Khách đã trả", debt="Còn nợ",
        cust_expr="DanhSachKhachHang", custid="Mã khách hàng",
        custcode="Mã KH",
        custname="Tên khách hàng", custtier="Nhóm khách hàng",
        timecol="Thời gian tạo",
        lines="DanhSachHoaDonChiTiet", loid="Mã hóa đơn", lproduct="Tên hàng",
        lkey="Mã hàng",
        lqty="Số lượng", lqty_base="Số lượng quy đổi", lrevenue="Thành tiền",
        lines_dedup=True,
        product_expr="DanhSachSanPham", pkey="Mã hàng", pname="Tên hàng",
        pcategory="Nhóm hàng(3 Cấp)", pprice="Giá bán",
        stock="BaoCaoTonKho", sname="Tên hàng", sqty="Tồn cuối kỳ",
        purch="DanhSachNhapHang", puoid="Mã nhập hàng", pudate="Thời gian",
        puamount="Cần trả NCC", pustatus="Trạng thái",
        pud="DanhSachChiTietNhapHang", pudoid="Mã nhập hàng", pudproduct="Mã hàng",
        pudqty="Số lượng", pudprice="Đơn giá", pudunit="ĐVT",
    ),
    "biz_109": dict(
        orders=("DuLieuBanHang", "DanhSachHoaDon"), oid="Mã hóa đơn", date="Thời gian",
        revenue="Tổng tiền hàng", total="Tổng sau giảm giá",
        status="Trạng thái", customer="Khách hàng", custcode="Mã KH",
        channel="Kênh bán", payment="Phương thức thanh toán",
        paid="Khách đã trả", debt="Còn nợ", staff="Người bán",
        timecol="Thời gian tạo",
        cust_expr=("DuLieuBanHang", "DanhSachKhachHang"), custid="Mã khách hàng",
        custname="Tên khách hàng", custphone="Điện thoại",
        lines="DanhSachHoaDonChiTiet", loid="Mã hóa đơn", lproduct="Tên hàng",
        lkey="Mã hàng",
        lqty="Số lượng", lqty_base="Số lượng quy đổi", lrevenue="Thành tiền",
        lunit="Đơn vị tính", lcost="Giá vốn",
        product_expr=("DuLieuBanHang", "DanhSachSanPham"), pkey="Mã hàng",
        pname="Tên hàng", pcategory="Nhóm hàng(3 Cấp)", pprice="Giá bán",
        stock=("DuLieuBanHang", "BaoCaoTonKho"), sname="Tên hàng", sqty="Tồn cuối kỳ",
    ),
    # ---------------- order-only ----------------
    "biz_110": dict(
        orders="danh_sach_hoa_don", oid="Mã bill", date="Ngày giao dịch",
        revenue="Tien hang", total="TongTien", status="Status", customer="Bên mua",
        paid="Da tra", debt="Chưa trả",
    ),
    # ---------------- ERP lower-case ----------------
    "biz_111": dict(
        orders="don_hang", oid="Mã chứng từ", date="NgayBan", revenue="Tổng bill",
        status="Xử lý", customer="Số KH", channel="Bán qua", payment="Phương thức TT",
        paid="Khách trả", debt="Còn lại",
        lines="chi_tiet_don", loid="Ma don", lproduct="ID SP", lqty="SL",
        lqty_base="SL quy đổi", lrevenue="T.Tiền", lunit="Đơn vị (tính)",
        product_expr="san_pham", pkey="SKU", pname="Sản phẩm", pcategory="Nhom hang",
        pprice="Giá",
        pay_expr="thanh_toan", payoid="Số HĐ", paydate="Thời gian thu",
        payamount="Tiền", paymethod="Phương thức",
        cust_expr="khach_hang", custid="ma_kh", custname="Khách lẻ/sỉ", custtier="Nhóm",
    ),
    "biz_123": dict(
        orders="don_hang", oid="MaHoaDon", date="NgayLap", revenue="TongTienHang",
        status="TinhTrang", customer="MaKhachHang", channel="KenhBanHang",
        payment="PhuongThucTT", paid="KhachDaTra", debt="ConPhaiThu",
        total="TongThanhToan",
        lines="chi_tiet_don", loid="MaHoaDon", lproduct="MaHangHoa", lqty="SL",
        lqty_base="SLQuyDoi", lrevenue="TriGia", lunit="DonViTinh", lcost="GiaVonLucBan",
        lines_dedup=True,
        product_expr="san_pham", pkey="MaHangHoa", pname="TenGoi", pcategory="DanhMuc",
        pprice="GiaBanLe", pcost="GiaVonHang",
        stock="the_kho", sname="MaHangHoa", sqty="TonCuoi",
        purch="chi_tiet_nhap", pudate=None, puproduct="MaHangHoa",
        puqty="SL", puamount=None, pusupplier="",
        pay_expr="thanh_toan", payoid="MaHoaDon", paydate="NgayGioThu",
        payamount="SoTienThu", paymethod="PhuongThuc",
        ph="lich_su_gia", phproduct="MaHangHoa", phdate="NgayApDung",
        phnew="GiaBanLe", phold=None,
        cust_expr="khach_hang", custid="MaKhachHang", custname="TenGoi",
        custtier="LoaiKhachHang", custbirth="ngay_sinh",
        staff="MaNhanVien", staff_expr="nhan_vien", staffkey="MaNhanVien",
        staffname="TenGoi", timecol="ThoiGianLap",
        ingr_expr="thong_tin_thuoc", ingrkey="MaHangHoa", ingrname="ThanhPhanChinh",
        rx="thong_tin_thuoc", rxkey="MaHangHoa", rxflag="BanTheoDon",
    ),
    "biz_127": dict(
        orders="don_hang", oid="Mã chứng từ", date="Ngày", revenue="Tổng đơn",
        status="Tình trạng", customer="Customer ID", channel="Loại bán",
        payment="Trả bằng", paid="Khách trả", debt="Còn nợ",
        lines="chi_tiet_don", loid="Mã đơn hàng", lproduct="Mã mặt hàng",
        lqty="SoLuong", lqty_base="Số lượng lẻ", lrevenue="Amount",
        lunit="DVT", lines_dedup=True,
        product_expr="san_pham", pkey="Mã sản phẩm bán", pname="Tên SP",
        pcategory="Danh mục", pprice="Giá niêm yết",
        cust_expr="khach_hang", custid="Mã KH", custname="Khách hàng (tên)",
        pay_expr="thanh_toan", payoid="Số CT", paydate="Ngày thu",
        payamount="Giá trị", paymethod="HTTT",
    ),
    "biz_129": dict(
        orders="don_hang", oid="Số phiếu", date="Ngày bán", revenue="Phải thu",
        status="Tình trạng đơn", customer="Mã khách mua",
        payment="Hình thức thanh toán", paid="Thanh toán", debt="Dư nợ",
        lines="chi_tiet_don", loid="Số CT", lproduct="Mã hàng bán", lqty="S.L",
        lqty_base="Quy ra ĐV lẻ", lrevenue="Tiền bán", lunit="ĐV tính",
        product_expr="san_pham", pkey="Mã HH", pname="Tên sản phẩm",
        pcategory="Nhom hang", pprice="Giá hiện tại",
        pay_expr="thanh_toan", payoid="Mã giao dịch", paydate="Thời điểm",
        payamount="Tiền", paymethod="PTTT",
        cust_expr="khach_hang", custid="Mã khách lẻ/sỉ", custname="KH",
        custtier="Nhóm",
    ),
    # ---------------- BanHang ERP ----------------
    "biz_124": dict(
        orders="BanHang_HoaDon", oid="Order ID", date="Ngày bán",
        revenue="Tong tien", status="Trạng thái", customer="Mã KH mua",
        channel="Nguồn đơn", payment="Phương thức TT", paid="Đã thu", debt="Còn nợ",
        lines="BanHang_ChiTietHoaDon", loid="Mã giao dịch", lproduct="Ma hang",
        lqty="Slg", lqty_base="SL cơ bản", lrevenue="Thanh tien", lunit="Đ.vị",
        lcost="Giá vốn lúc bán", lines_dedup=True,
        product_expr="BanHang_HangHoa", pkey="ma_sp", pname="Món",
        pcategory="Phân loại", pprice="Giá", pcost="Giá vốn hiện tại",
        stock="ton_kho", sname="ID SP", sqty="Ton kho",
        purch="SoTay_NhapHang", pudate="Ngày nhập", puproduct="Product",
        puqty="SL nhập", puamount="Thành tiền", pusupplier="Nhà cung cấp",
        staff="Mã NV bán", timecol="Giờ tạo đơn",
        ingr_expr="BanHang_Thuoc", ingrkey="Mã HH", ingrname="Hoạt chất",
        pay_expr="BanHang_PhieuThu", payoid="Mã bill", paydate="Thời gian thu",
        payamount="Số tiền thu", paymethod="PTTT",
        ph="BanHang_LichSuGia", phproduct="Mã sản phẩm", phdate="Ngày áp dụng",
        phnew="Giá mới", phold="Giá cũ",
        cust_expr="BanHang_KhachHang", custid="Customer ID", custname="ten_kh",
        custtier="Hạng", custbirth="Ngày sinh",
    ),
}


# --------------------------------------------------------------------------
# extended sources: purchase headers/detail, lots, stock transactions,
# unit conversions, prescription flags
# --------------------------------------------------------------------------

_EXTRA = {
    "biz_106": dict(
        pay_expr="SoQuy", payoid="Mã hóa đơn", paydate="Thời gian",
        payamount="Giá trị", paymethod="Phương thức thanh toán",
        purch="DanhSachNhapHang", puoid="Mã nhập hàng", pudate="Thời gian",
        puamount="Cần trả NCC", pustatus="Trạng thái",
        pud="DanhSachChiTietNhapHang", pudoid="Mã nhập hàng", pudproduct="Mã hàng",
        pudqty="Số lượng", pudprice="Đơn giá", pudunit="ĐVT",
        conv="DanhSachDonViTinh", convkey="Mã hàng", convunit="ĐVT", convratio="Quy đổi",
    ),
    "biz_108": dict(
        purch="DanhSachNhapHang", puoid="Mã nhập hàng", pudate="Thời gian",
        puamount="Cần trả NCC", pustatus="Trạng thái",
        pud="DanhSachChiTietNhapHang", pudoid="Mã nhập hàng", pudproduct="Mã hàng",
        pudqty="Số lượng", pudprice="Đơn giá", pudunit="ĐVT",
    ),
    "biz_109": dict(
        pay_expr=("DuLieuBanHang", "SoQuy"), payoid="Mã hóa đơn",
        paydate="Thời gian", payamount="Giá trị", paymethod="Phương thức thanh toán",
        purch=("DuLieuBanHang", "DanhSachNhapHang"), puoid="Mã nhập hàng",
        pudate="Thời gian", puamount="Cần trả NCC", pustatus="Trạng thái",
        pud=("DuLieuBanHang", "DanhSachChiTietNhapHang"), pudoid="Mã nhập hàng",
        pudproduct="Mã hàng", pudqty="Số lượng", pudprice="Đơn giá", pudunit="ĐVT",
        conv=("DuLieuBanHang", "DanhSachDonViTinh"), convkey="Mã hàng",
        convunit="ĐVT", convratio="Quy đổi",
    ),
    "biz_119": dict(
        purch="DanhSachNhapHang", puoid="Mã nhập hàng", pudate="Thời gian",
        puamount="Cần trả NCC", pustatus="Trạng thái",
        pud="DanhSachChiTietNhapHang", pudoid="Mã nhập hàng", pudproduct="Mã hàng",
        pudqty="Số lượng", pudprice="Đơn giá", pudunit="ĐVT",
        lot="DanhSachLoHang", lotid="Lô", lotproduct="Mã hàng",
        lotexpiry="Hạn sử dụng", lotqty="Số lượng (ĐVT cơ bản)", lotpurch="Mã nhập hàng",
        rx="DanhSachThuoc", rxkey="Mã hàng", rxflag="Thuốc kê đơn",
        ingr_expr="DanhSachThuoc", ingrkey="Mã hàng", ingrname="Hoạt chất",
    ),
    "biz_120": dict(
        purch="DanhSachNhapHang", puoid="Mã nhập hàng", pudate="Thời gian",
        puamount="Cần trả NCC", pustatus="Trạng thái",
        pud="DanhSachChiTietNhapHang", pudoid="Mã nhập hàng", pudproduct="Mã hàng",
        pudqty="Số lượng", pudprice="Đơn giá", pudunit="ĐVT",
        lot="DanhSachLoHang", lotid="Lô", lotproduct="Mã hàng",
        lotexpiry="Hạn sử dụng", lotqty="Số lượng (ĐVT cơ bản)", lotpurch="Mã nhập hàng",
        rx="DanhSachThuoc", rxkey="Mã hàng", rxflag="Thuốc kê đơn",
        ingr_expr="DanhSachThuoc", ingrkey="Mã hàng", ingrname="Hoạt chất",
    ),
    "biz_121": dict(
        sku_expr=("DuLieuXuat", "DanhSachSanPham"), skukey="Mã SKU", skuname="Tên sản phẩm",
        purch=("DuLieuXuat", "DonNhapHang"), puoid="Mã đơn nhập", pudate="Ngày nhập",
        pud=("DuLieuXuat", "DonNhapHang_ChiTiet"), pudoid="Mã đơn nhập",
        pudproduct="Mã SKU", pudqty="Số lượng nhập",
        lot=("DuLieuXuat", "DonNhapHang_ChiTiet"), lotid="Mã lô",
        lotproduct="Mã SKU", lotexpiry="Hạn sử dụng", lotqty="Số lượng nhập",
        lotpurch="Mã đơn nhập",
        lotsold=("DuLieuXuat", "DonHang_Lo"), lotsoldlot="Mã lô",
        lotsoldoid="Mã đơn hàng", lotsoldqty="Số lượng", lotsoldret="Số lượng trả",
        conv=("DuLieuXuat", "DanhSachQuyDoi"), convkey="Tên sản phẩm",
        convunit="Đơn vị quy đổi", convratio="Tỉ lệ quy đổi",
        rx=("DuLieuXuat", "DanhSachThuoc"), rxkey="Mã SKU", rxflag="Thuốc kê đơn",
        ingr_expr=("DuLieuXuat", "DanhSachThuoc"), ingrkey="Mã SKU", ingrname="Hoạt chất",
    ),
    "biz_122": dict(
        sku_expr="DanhSachSanPham", skukey="Mã SKU", skuname="Tên sản phẩm",
        purch="DonNhapHang", puoid="Mã đơn nhập", pudate="Ngày nhập",
        pud="DonNhapHang_ChiTiet", pudoid="Mã đơn nhập", pudproduct="Mã SKU",
        pudqty="Số lượng nhập",
        lot="DonNhapHang_ChiTiet", lotid="Mã lô", lotproduct="Mã SKU",
        lotexpiry="Hạn sử dụng", lotqty="Số lượng nhập", lotpurch="Mã đơn nhập",
        lotsold=["DonHang_Lo_1", "DonHang_Lo_2"], lotsoldlot="Mã lô",
        lotsoldoid="Mã đơn hàng", lotsoldqty="Số lượng", lotsoldret="Số lượng trả",
        conv="DanhSachQuyDoi", convkey="Tên sản phẩm", convunit="Đơn vị quy đổi",
        convratio="Tỉ lệ quy đổi",
        rx="DanhSachThuoc", rxkey="Mã SKU", rxflag="Thuốc kê đơn",
        ingr_expr="DanhSachThuoc", ingrkey="Mã SKU", ingrname="Hoạt chất",
    ),
    "biz_123": dict(
        stock="the_kho", sname="MaHangHoa", sqty="TonCuoi", sdate="NgayGioPhatSinh",
        stockt="the_kho", stocktproduct="MaHangHoa", stocktdate="NgayGioPhatSinh",
        stocktqty="SLQuyDoi", stocktbalance="TonCuoi",
        purch="phieu_nhap", puoid="MaPhieuNhap", pudate="NgayNhapKho",
        puamount="TongGiaTriNhap", pustatus="TinhTrang",
        pud="chi_tiet_nhap", pudoid="MaPhieuNhap", pudproduct="MaHangHoa",
        pudqty="SL", pudprice="DonGiaNhap", pudunit="DonViTinh",
        lot="lo_hang", lotid="MaLo", lotproduct="MaHangHoa",
        lotexpiry="HanSuDung", lotqty="SLNhapQuyDoi", lotprice="DonGiaNhap",
        lotpurch="MaPhieuNhap",
        lotsold="chi_tiet_don_lo", lotsoldlot="MaLo", lotsoldoid="MaHoaDon",
        lotsoldqty="SLQuyDoi", lotsoldret="SLTraQuyDoi",
    ),
    "biz_124": dict(
        puoid="Số phiếu",
        lot="BanHang_LoHang", lotid="Lô", lotproduct="Mã món",
        lotexpiry="HSD", lotqty="SL nhập (ĐVT cơ bản)", lotpurch="Mã phiếu nhập",
        lotsold="BanHang_BanTheoLo", lotsoldlot="Lô", lotsoldoid="Mã hóa đơn",
        lotsoldqty="SL quy ra lẻ", lotsoldret="SL trả (ĐVT cơ bản)",
        conv="BanHang_DonViQuyDoi", convkey="Mã sp", convunit="Đơn vị",
        convratio="Bằng",
        rx="BanHang_Thuoc", rxkey="Mã HH", rxflag="Kê đơn",
    ),
    "biz_117": dict(puoid="Số phiếu"),
    "biz_105": dict(puoid="Số phiếu"),
}
for _b, _x in _EXTRA.items():
    if _b in _SPECS_RAW:
        _SPECS_RAW[_b].update(_x)


def _resolve_expr(data: dict, expr):
    """Turn a logical frame reference into a Python expression.

    - str: top-level frame name
    - tuple(container, sheet): nested dict access
    - list: concatenate several frames
    """
    if expr is None:
        return None
    if isinstance(expr, list):
        parts = [_resolve_expr(data, e) for e in expr]
        return "pd.concat([" + ", ".join(f"_flat({p})" for p in parts) + "], ignore_index=True)"
    if isinstance(expr, tuple):
        ck = resolve_key(data, expr[0])
        sub = data[ck]
        if isinstance(sub, dict):
            sk = resolve_key(sub, expr[1])
            return f"_frame({_q(ck)})[{_q(sk)}]"
        return f"_frame({_q(ck)})"
    return f"_frame({_q(resolve_key(data, expr))})"


def _frame_columns(data: dict, expr) -> list:
    if expr is None:
        return []
    if isinstance(expr, list):
        cols = []
        for e in expr:
            cols.extend(_frame_columns(data, e))
        return cols
    if isinstance(expr, tuple):
        ck = resolve_key(data, expr[0])
        sub = data[ck]
        if isinstance(sub, dict):
            sk = resolve_key(sub, expr[1])
            return list(sub[sk].columns)
        return list(sub.columns)
    val = data[resolve_key(data, expr)]
    if isinstance(val, dict):
        cols = []
        for d in val.values():
            if hasattr(d, "columns"):
                cols.extend(list(d.columns))
        return cols
    return list(val.columns)


def resolve_col(columns, name):
    """Resolve a logical column name against real columns."""
    if not name:
        return None
    if name in columns:
        return name
    target = _norm_key(name)
    for c in columns:
        if _norm_key(c) == target:
            return c
    for c in columns:
        if target in _norm_key(c):
            return c
    for c in columns:
        if _norm_key(c) in target:
            return c
    return name


_COL_FIELDS = [
    "oid", "date", "revenue", "status", "customer", "channel", "payment",
    "paid", "debt",
    "loid", "ldate", "lproduct", "lqty", "lqty_base", "lrevenue", "lunit",
    "lcost",
    "custcode",
    "pkey", "pname", "pcategory", "pprice", "pcost",
    "sname", "sqty", "sdate",
    "puoid", "pudate", "puproduct", "puqty", "puamount", "pusupplier",
    "pustatus",
    "pudoid", "puddate", "pudproduct", "pudqty", "pudprice", "pudunit",
    "stocktproduct", "stocktdate", "stocktqty", "stocktbalance",
    "lotid", "lotproduct", "lotexpiry", "lotqty", "lotprice", "lotpurch",
    "lotsoldlot", "lotsoldoid", "lotsolddate", "lotsoldqty", "lotsoldret",
    "convkey", "convunit", "convratio",
    "rxkey", "rxflag", "ingrkey", "ingrname",
    "payoid", "paydate", "payamount", "paymethod",
    "phproduct", "phdate", "phnew", "phold",
    "custid", "custname", "custtier", "custbirth",
]


def build_spec(data: dict, raw: dict) -> dict:
    """Resolve all logical frame/column names in a raw spec against actual data."""
    s = dict(raw)

    # ---- frames ----
    orders_src = s.get("orders")
    lines_src = s.get("lines")
    sales_src = s.get("sales")
    if orders_src is None and sales_src is not None:
        # flat sales file is line-level; orders get derived from it
        lines_src = sales_src

    s["orders_expr"] = _resolve_expr(data, orders_src)
    s["lines_expr"] = _resolve_expr(data, lines_src)

    if sales_src is not None and s.get("lines") is None:
        s["loid"] = s.get("loid") or s.get("oid")
        s["ldate"] = s.get("ldate") or s.get("date")
        s["lproduct"] = s.get("lproduct") or s.get("product")
        s["lqty"] = s.get("lqty") or s.get("qty")
        s["lqty_base"] = s.get("lqty_base") or s.get("qty_base")
        s["lrevenue"] = s.get("lrevenue") or s.get("revenue")
        s["lunit"] = s.get("lunit") or s.get("unit")
        # only de-duplicate when several files were concatenated (overlapping exports)
        s["lines_dedup"] = s.get("lines_dedup", isinstance(sales_src, (list, tuple)))

    # keep raw refs for column resolution (s[...] becomes a rendered expression)
    raw_products = s.get("product_expr")
    raw_stock = s.get("stock")
    raw_purch = s.get("purch")
    raw_pud = s.get("pud")
    raw_stockt = s.get("stockt")
    raw_lot = s.get("lot")
    raw_lotsold = s.get("lotsold")
    raw_conv = s.get("conv")
    raw_rx = s.get("rx")
    raw_sku = s.get("sku_expr")
    raw_ingr = s.get("ingr_expr")
    raw_pay = s.get("pay_expr")
    raw_ph = s.get("ph")
    raw_dv = s.get("deliv")
    raw_cust = s.get("cust_expr")

    s["product_expr"] = _resolve_expr(data, raw_products)
    s["stock_expr"] = _resolve_expr(data, raw_stock)
    s["purch_expr"] = _resolve_expr(data, raw_purch)
    s["pud_expr"] = _resolve_expr(data, raw_pud)
    s["stockt_expr"] = _resolve_expr(data, raw_stockt)
    s["lot_expr"] = _resolve_expr(data, raw_lot)
    s["lotsold_expr"] = _resolve_expr(data, raw_lotsold)
    s["conv_expr"] = _resolve_expr(data, raw_conv)
    s["rx_expr"] = _resolve_expr(data, raw_rx)
    s["custcode"] = resolve_col(_frame_columns(data, orders_src), s.get("custcode")) if s.get("custcode") else None
    s["sku_expr"] = _resolve_expr(data, raw_sku)
    s["ingr_expr"] = _resolve_expr(data, raw_ingr)
    s["pay_expr"] = _resolve_expr(data, raw_pay)
    s["ph_expr"] = _resolve_expr(data, raw_ph)
    s["deliv_expr"] = _resolve_expr(data, raw_dv)
    s["cust_expr"] = _resolve_expr(data, raw_cust)

    # ---- columns ----
    ocols = _frame_columns(data, orders_src)
    lcols = _frame_columns(data, lines_src)
    pcols = _frame_columns(data, raw_products)
    scols = _frame_columns(data, raw_stock)
    ucols = _frame_columns(data, raw_purch)
    udcols = _frame_columns(data, raw_pud)
    stcols = _frame_columns(data, raw_stockt)
    ltcols = _frame_columns(data, raw_lot)
    lscols = _frame_columns(data, raw_lotsold)
    cvcols = _frame_columns(data, raw_conv)
    rxcols = _frame_columns(data, raw_rx)
    ycols = _frame_columns(data, raw_pay)
    hcols = _frame_columns(data, raw_ph)
    dcols = _frame_columns(data, raw_dv)
    ccols = _frame_columns(data, raw_cust)

    group = {
        "oid": ocols, "date": ocols, "revenue": ocols, "status": ocols,
        "customer": ocols, "channel": ocols, "payment": ocols,
        "paid": ocols, "debt": ocols,
        "loid": lcols, "ldate": lcols, "lproduct": lcols, "lqty": lcols,
        "lqty_base": lcols, "lrevenue": lcols, "lunit": lcols, "lcost": lcols,
        "pkey": pcols, "pname": pcols, "pcategory": pcols, "pprice": pcols,
        "pcost": pcols,
        "sname": scols, "sqty": scols, "sdate": scols,
        "puoid": ucols, "pudate": ucols, "puproduct": ucols, "puqty": ucols,
        "puamount": ucols, "pusupplier": ucols, "pustatus": ucols,
        "pudoid": udcols, "puddate": udcols, "pudproduct": udcols,
        "pudqty": udcols, "pudprice": udcols, "pudunit": udcols,
        "stocktproduct": stcols, "stocktdate": stcols, "stocktqty": stcols,
        "stocktbalance": stcols,
        "lotid": ltcols, "lotproduct": ltcols, "lotexpiry": ltcols,
        "lotqty": ltcols, "lotprice": ltcols, "lotpurch": ltcols,
        "lotsoldlot": lscols, "lotsoldoid": lscols, "lotsolddate": lscols,
        "lotsoldqty": lscols, "lotsoldret": lscols,
        "convkey": cvcols, "convunit": cvcols, "convratio": cvcols,
        "rxkey": rxcols, "rxflag": rxcols,
        "payoid": ycols, "paydate": ycols, "payamount": ycols, "paymethod": ycols,
        "phproduct": hcols, "phdate": hcols, "phnew": hcols, "phold": hcols,
        "ddate": dcols, "doid": dcols, "dline": dcols, "dqty": dcols,
        "custid": ccols, "custname": ccols, "custtier": ccols, "custbirth": ccols,
    }
    for f in _COL_FIELDS:
        if s.get(f):
            s[f] = resolve_col(group.get(f, []), s[f])

    s["has_oid"] = bool((orders_src is not None and s.get("oid")) or s.get("loid"))
    return s
