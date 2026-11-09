"""Self-generate *verified* SFT records from the real business data.

No external LLM is used.  For every question we

1. canonicalise the business data into `orders` / `lines` (+ optional
   products / stock / purchases / payments / price_history / customers),
2. parse the Vietnamese time expression,
3. generate a handful of candidate pandas solutions,
4. execute each on the real data and keep the first one that matches the
   gold answer exactly,
5. emit a self-contained `prepare + intent` code block as the SFT target.

Because the emitted code is executed and compared with the gold answer, every
record in the output is guaranteed correct on that business.

Usage:
    python code/selfgen.py --limit 200
    python code/selfgen.py --out sft_selfgen.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "code"))

from loader import load_business, describe_business  # noqa: E402
from adapters import _SPECS_RAW, build_spec, render_prepare  # noqa: E402
from scorer import match_answer  # noqa: E402
from agent import infer_type, SYSTEM_PROMPT, build_prompt  # noqa: E402


# ---------------------------------------------------------------------------
# text helpers
# ---------------------------------------------------------------------------
def strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.replace("đ", "d").replace("Đ", "D")


_CAL_CACHE = {}


def _load_calendar():
    if "df" not in _CAL_CACHE:
        _CAL_CACHE["df"] = pd.read_csv(ROOT / "train" / "calendar.csv", parse_dates=["date"])
    return _CAL_CACHE["df"]


def tet_span(year):
    """Return (start, end) for the Tet season of lunar year `year`."""
    cal = _load_calendar()
    a = cal[(cal["lunar_day"] == 23) & (cal["lunar_month"] == 12) & (cal["lunar_year"] == year - 1)]
    b = cal[(cal["lunar_day"] == 10) & (cal["lunar_month"] == 1) & (cal["lunar_year"] == year)]
    if not len(a) or not len(b):
        return None, None
    return a["date"].min().normalize(), b["date"].max().normalize()


def norm_q(s: str) -> str:
    s = strip_accents(str(s)).lower()
    s = re.sub(r"[^a-z0-9%/<>=\-\. ]+", " ", s)
    s = re.sub(r"([aeiou])\1+", r"\1", s)
    s = re.sub(r"f\b", "", s)
    s = re.sub(r"\bthangs\b|\bthangf\b", "thang", s)
    s = re.sub(r"\bnhiu\b|\bnheu\b", "nhieu", s)
    s = re.sub(r"\bnhoms\b", "nhom", s)
    s = re.sub(r"\btrowr\b|\btror\b", "tro", s)
    s = re.sub(r"\bleen\b", "len", s)
    s = re.sub(r"\bhets\b", "het", s)
    s = re.sub(r"\bbnhiu\b|\bbnhieu\b|\bbn\b", "bao nhieu", s)
    s = re.sub(r"\bcuwar\b|\bcuar\b|\bcuwa\b", "cua", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_name(s: str) -> str:
    s = strip_accents(str(s)).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _d(s):
    return pd.Timestamp(s).date().isoformat()


def _last_day(y: int, m: int) -> str:
    return (pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0)).date().isoformat()


def _shift_month(y: int, m: int, k: int):
    t = pd.Timestamp(y, m, 1) + pd.DateOffset(months=k)
    return t.year, t.month


# ---------------------------------------------------------------------------
# time-span parsing
# ---------------------------------------------------------------------------
def mentioned_months(qraw: str, asof: str) -> list[tuple[int, int]]:
    """All explicit month mentions, in text order."""
    q = norm_q(qraw)
    out = []
    for m in re.finditer(r"thangs?\s+(\d{1,2})\s*[/\-.]\s*(\d{4})", q):
        mo, y = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            out.append((y, mo))
    for m in re.finditer(r"thang\s+(\d{1,2})\s+nam\s+(\d{4})", q):
        mo, y = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            out.append((y, mo))
    # bare M/YYYY (e.g. "tháng 11/2025, 12/2025 và 1/2026")
    for m in re.finditer(r"(?<![\d/])(\d{1,2})[/\-](\d{4})(?![\d/])", q):
        mo, y = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            out.append((y, mo))
    # de-dup
    seen = set()
    res = []
    for x in out:
        if x not in seen:
            seen.add(x)
            res.append(x)
    return res


def parse_spans(qraw: str, asof: str) -> list[dict]:
    """Return candidate time spans, most specific first."""
    q = norm_q(qraw)
    a = pd.Timestamp(asof)
    spans: list[dict] = []

    def add(kind, start, end, label):
        if start is not None:
            start = _d(start)
        if end is not None:
            end = _d(end)
        spans.append(dict(kind=kind, start=start, end=end, label=label))

    # explicit "tu <date> den <date>" range has the highest priority
    for m in re.finditer(
        r"tu\s*(?:ngay\s*)?(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\s*"
        r"(?:den(?:\s*het)?|toi|het)\s*(?:ngay\s*)?(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", q):
        try:
            s0 = pd.Timestamp(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            e0 = pd.Timestamp(int(m.group(6)), int(m.group(5)), int(m.group(4)))
        except ValueError:
            continue
        if e0 >= s0:
            add("range", s0, e0, f"tu {s0.date()} den {e0.date()}")

    # Tet season (lunar calendar)
    if re.search(r"\btet\b", q):
        _ty = None
        _mt = re.search(r"\btet\b[^0-9]{0,20}(20\d\d)|(20\d\d)[^0-9]{0,20}\btet\b", q)
        if _mt:
            _ty = int(_mt.group(1) or _mt.group(2))
        if _ty is None:
            _ty = a.year
        _ts, _te = tet_span(_ty)
        if _ts is not None:
            add("range", _ts, _te, f"tet {_ty}")

    # ------------------------------------------------------------------
    # 1. cumulative expressions ("tu dau nam den het hom nay")
    # ------------------------------------------------------------------
    m_end = re.search(
        r"(?:den het|den|toi|het)\s*(?:ngay\s*)?(\d{1,2})[/\-.]?(\d{1,2})[/\-.]?(\d{4})", q
    )
    end_ts = None
    if m_end:
        try:
            end_ts = pd.Timestamp(int(m_end.group(3)), int(m_end.group(2)), int(m_end.group(1)))
        except ValueError:
            end_ts = None
    if re.search(r"dau nam|tu (ngay )?1/1|tu dau thang 1", q) and not re.search(r"nam (?:19|20)\d\d", q):
        add("cumulative", pd.Timestamp(a.year, 1, 1), end_ts or a, f"dau nam {a.year}")
    elif re.search(r"nam nay", q) and not re.search(r"nam (?:19|20)\d\d", q):
        add("cumulative", pd.Timestamp(a.year, 1, 1), a, f"nam nay {a.year}")
    if re.search(r"dau nam", q) and re.search(r"nam (?:19|20)\d\d", q):
        _yy = int(re.search(r"nam ((?:19|20)\d\d)", q).group(1))
        add("cumulative", pd.Timestamp(_yy, 1, 1), pd.Timestamp(_yy, 12, 31), f"dau nam {_yy}")
    if re.search(r"dau thang", q):
        add("cumulative", a.replace(day=1), end_ts or a, "dau thang")
    if re.search(r"den het|tinh den|den ngay", q) and end_ts is not None and not re.search(r"dau nam|dau thang", q):
        add("cumulative", None, end_ts, f"den {end_ts.date()}")

    # ------------------------------------------------------------------
    # 2. "N ngay ke tu ngay X" / "N ngay gan nhat"
    # ------------------------------------------------------------------
    for m in re.finditer(
        r"(\d+)\s*ngay\s*ke tu\s*(?:ngay\s*)?(\d{1,2})[/\-.]?(\d{1,2})[/\-.]?(\d{4})", q
    ):
        n = int(m.group(1))
        try:
            s0 = pd.Timestamp(int(m.group(4)), int(m.group(3)), int(m.group(2)))
        except ValueError:
            continue
        add("range", s0, s0 + pd.Timedelta(days=n - 1), f"{n} ngay tu {s0.date()}")
        add("range", s0 - pd.Timedelta(days=n), s0 - pd.Timedelta(days=1),
            f"{n} ngay truoc {s0.date()}")
    for m in re.finditer(r"(\d+)\s*ngay\s*(?:gan nhat|tro lai|vua qua|qua)", q):
        n = int(m.group(1))
        add("range", a - pd.Timedelta(days=n - 1), a, f"{n} ngay gan nhat")

    # ------------------------------------------------------------------
    # 3. explicit month ranges
    # ------------------------------------------------------------------
    for m in re.finditer(
        r"tu\s+thang\s+(\d{1,2})\s*(?:[/\-.]\s*(\d{4}))?\s*(?:den|toi|qua)\s*thang\s+(\d{1,2})\s*(?:[/\-.]\s*(\d{4}))?",
        q,
    ):
        m1 = int(m.group(1)); y1 = int(m.group(2)) if m.group(2) else a.year
        m2 = int(m.group(3)); y2 = int(m.group(4)) if m.group(4) else y1
        if y2 < y1:
            y2 = y1
        if 1 <= m1 <= 12 and 1 <= m2 <= 12:
            add("range", pd.Timestamp(y1, m1, 1), pd.Timestamp(_last_day(y2, m2)),
                f"thang {m1}/{y1} - {m2}/{y2}")
    for m in re.finditer(
        r"(\d+)\s*thang\s*lien\s*(?:nhau|tiep)\s*(?:ket thuc|den|o)\s*(?:thang\s*)?(\d{1,2})\s*[/\-.]\s*(\d{4})", q
    ):
        n = int(m.group(1)); mo = int(m.group(2)); y = int(m.group(3))
        y0, m0 = _shift_month(y, mo, -(n - 1))
        add("range", pd.Timestamp(y0, m0, 1), pd.Timestamp(_last_day(y, mo)),
            f"{n} thang den {mo}/{y}")

    # multiple explicit months -> a covering range
    months = mentioned_months(qraw, asof)
    if len(months) >= 2:
        ms = sorted(months)
        add("range", pd.Timestamp(ms[0][0], ms[0][1], 1),
            pd.Timestamp(_last_day(ms[-1][0], ms[-1][1])), "nhieu thang")

    # ------------------------------------------------------------------
    # 4. relative day / week / month
    # ------------------------------------------------------------------
    if re.search(r"hom qua|hqua|bua qua|bua hom qua|qua hom qua", q):
        d = a - pd.Timedelta(days=1)
        add("day", d, d, "hom qua")
    if re.search(r"hom nay|ho+m nay|hnay|bua nay|hom ni", q):
        add("day", a, a, "hom nay")
    mon = a - pd.Timedelta(days=a.weekday())
    if re.search(r"tuan truoc|tuan roi|tuan trc|tuan vua roi", q):
        add("range", mon - pd.Timedelta(days=7), mon - pd.Timedelta(days=1), "tuan truoc")
    if re.search(r"tuan nay", q):
        add("range", mon, a, "tuan nay")
    if re.search(r"thang truoc|thang lien truoc|thang vua roi", q):
        y, mo = _shift_month(a.year, a.month, -1)
        add("month", pd.Timestamp(y, mo, 1), pd.Timestamp(_last_day(y, mo)), f"thang {mo}/{y}")
    if re.search(r"thang nay|thang hien tai", q):
        add("month", a.replace(day=1), a, "thang nay")

    # ------------------------------------------------------------------
    # 5. explicit day / month / quarter / year
    # ------------------------------------------------------------------
    for m in re.finditer(r"(?<!\d)(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})(?!\d)", q):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            ts = pd.Timestamp(y, mo, d)
        except ValueError:
            continue
        add("day", ts, ts, f"ngay {ts.date()}")

    for m in re.finditer(r"thangs?\s+(\d{1,2})\s*[/\-.]\s*(\d{4})", q):
        mo, y = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            add("month", pd.Timestamp(y, mo, 1), pd.Timestamp(_last_day(y, mo)), f"thang {mo}/{y}")
    for m in re.finditer(r"thang\s+(\d{1,2})\s+nam\s+(\d{4})", q):
        mo, y = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            add("month", pd.Timestamp(y, mo, 1), pd.Timestamp(_last_day(y, mo)), f"thang {mo}/{y}")
    for m in re.finditer(r"thang\s+(\d{1,2})(?!\s*[/\-.]?\s*\d)", q):
        mo = int(m.group(1))
        if 1 <= mo <= 12 and not re.search(r"thang\s+%d\s*(?:[/\-.]|\s+nam)" % mo, q):
            add("month", pd.Timestamp(a.year, mo, 1), pd.Timestamp(_last_day(a.year, mo)),
                f"thang {mo}/{a.year}")

    for m in re.finditer(r"quy\s*(\d)\s*(?:[/\-.]\s*(\d{4})|nam\s+(\d{4}))?", q):
        qq = int(m.group(1))
        y = int(m.group(2) or m.group(3) or a.year)
        if 1 <= qq <= 4:
            sm = (qq - 1) * 3 + 1
            em = sm + 2
            add("quarter", pd.Timestamp(y, sm, 1), pd.Timestamp(_last_day(y, em)), f"quy {qq}/{y}")

    for m in re.finditer(r"nam\s+(\d{4})", q):
        y = int(m.group(1))
        add("year", pd.Timestamp(y, 1, 1), pd.Timestamp(y, 12, 31), f"nam {y}")

    # de-duplicate while preserving order
    seen = set()
    out = []
    for s in spans:
        key = (s["start"], s["end"], s["kind"])
        if key in seen:
            continue
        seen.add(key)
        if s["start"] and pd.Timestamp(s["start"]) > a:
            continue
        if s["end"] and pd.Timestamp(s["end"]) > a:
            s = dict(s)
            s["end"] = a.date().isoformat()
        out.append(s)
    return out


def span_filter(var: str, span: dict | None) -> str:
    if not span:
        return var
    conds = []
    if span.get("start"):
        conds.append(f"({var}['_date'] >= pd.Timestamp({span['start']!r}))")
    if span.get("end"):
        conds.append(f"({var}['_date'] < pd.Timestamp({span['end']!r}) + pd.Timedelta(days=1))")
    if not conds:
        return var
    return var + "[" + " & ".join(conds) + "]"


# ---------------------------------------------------------------------------
# candidate code builders
# ---------------------------------------------------------------------------
def _head(table: str, span: dict | None, bad: bool = True, var: str = "_o") -> str:
    if bad:
        code = f"{var} = {table}[~{table}['_bad']].copy()\n"
    else:
        code = f"{var} = {table}.copy()\n"
    if span and (span.get("start") or span.get("end")):
        code += f"{var} = {span_filter(var, span)}\n"
    return code


def _num(x: str) -> str:
    return f"int(round(float({x})))"


def cand_revenue(span, use_lines=False, bad=True):
    table = "lines" if use_lines else "orders"
    var = "_l" if use_lines else "_o"
    code = _head(table, span, bad, var)
    code += f"RESULT = {_num(var + chr(91) + chr(39) + '_revenue' + chr(39) + chr(93) + '.sum()')}\n"
    return code


def cand_order_count(span, bad=True):
    code = _head("orders", span, bad, "_o")
    code += "RESULT = int(_o['_oid'].nunique())\n"
    return code


def cand_line_count(span, bad=True):
    code = _head("lines", span, bad, "_l")
    code += "RESULT = int(len(_l))\n"
    return code


def cand_qty(span, base=True, bad=True):
    code = _head("lines", span, bad, "_l")
    col = "_qty_base" if base else "_qty"
    code += f"RESULT = {_num('_l' + chr(91) + repr(col) + chr(93) + '.sum()')}\n"
    return code


def cand_qty_unit(span, unit):
    code = _head("lines", span, True, "_l")
    code += f"_l = _l[_l['_unit'].map(normalize_text) == {norm_name(unit)!r}]\n"
    code += f"RESULT = {_num('_l' + chr(91) + repr('_qty') + chr(93) + '.sum()')}\n"
    return code


def cand_avg_order(span, bad=True, use_lines=False):
    table = "lines" if use_lines else "orders"
    var = "_l" if use_lines else "_o"
    code = _head(table, span, bad, var)
    code += (
        f"_rev = float({var}['_revenue'].sum())\n"
        f"_n = int({var}['_oid'].nunique())\n"
        "RESULT = round(_rev / _n, 2) if _n else 0\n"
    )
    return code


def cand_cancel_count(span, mask="cancelled"):
    code = _head("orders", span, False, "_o")
    col = "_cancelled" if mask == "cancelled" else "_bad"
    code += f"RESULT = int(_o.loc[_o['{col}'], '_oid'].nunique())\n"
    return code


def cand_cancel_rate(span, denom="total", mask="cancelled"):
    code = _head("orders", span, False, "_o")
    col = "_cancelled" if mask == "cancelled" else "_bad"
    code += f"_c = int(_o.loc[_o['{col}'], '_oid'].nunique())\n"
    if denom == "nonreturned":
        code += (
            "_t = int(_o.loc[~_o['_status'].astype(str).str.contains('tra hang|tra lai|hoan tra|hoan hang|doi tra', case=False, na=False), '_oid'].nunique())\n"
        )
    else:
        code += "_t = int(_o['_oid'].nunique())\n"
    code += "RESULT = f'{round(_c / _t * 100, 2):.2f}%' if _t else '0.00%'\n"
    return code


def cand_best_day(span, use_lines=False):
    table = "lines" if use_lines else "orders"
    var = "_l" if use_lines else "_o"
    code = _head(table, span, True, var)
    code += (
        f"_g = {var}.groupby({var}['_date'].dt.date)['_revenue'].sum()\n"
        "RESULT = str(_g.idxmax()) if len(_g) else 'unanswerable'\n"
    )
    return code


def cand_max_day_rev(span, use_lines=False):
    table = "lines" if use_lines else "orders"
    var = "_l" if use_lines else "_o"
    code = _head(table, span, True, var)
    code += (
        f"_g = {var}.groupby({var}['_date'].dt.date)['_revenue'].sum()\n"
        "RESULT = int(round(float(_g.max()))) if len(_g) else 0\n"
    )
    return code


def cand_month_series(span_months, agg="orders"):
    """Revenue for a list of (y, m) months."""
    lines = ["_m = orders[~orders['_bad']].copy()", "_m['_y'] = _m['_date'].dt.year",
             "_m['_mo'] = _m['_date'].dt.month"]
    lines.append("_s = _m.groupby(['_y', '_mo'])['_revenue'].sum()")
    vals = []
    for (y, m) in span_months:
        vals.append(f"_s.get(({y}, {m}), 0)")
    lines.append("_vals = [" + ", ".join(vals) + "]")
    lines.append("RESULT = [int(round(float(v))) for v in _vals]")
    return "\n".join(lines) + "\n"


def cand_pct_change_periods(start1, end1, start2, end2, product=None, by="revenue", use_lines=False,
                            exclude_bad=True):
    """Percent change between two periods: (period2 - period1) / period1 * 100."""
    if product:
        use_lines = True
    table = "lines" if use_lines else "orders"
    var = "_l" if use_lines else "_o"
    if exclude_bad:
        code = f"{var} = {table}[~{table}['_bad']].copy()\n"
    else:
        code = f"{var} = {table}.copy()\n"
    if product:
        code += f"{var} = {var}[{var}['_product'].map(normalize_text) == {product!r}]\n"
    col = {"revenue": "_revenue", "qty": "_qty", "qty_base": "_qty_base"}[by]
    code += (
        f"_a = float({var}[({var}['_date'] >= pd.Timestamp({start1!r})) & ({var}['_date'] < pd.Timestamp({end1!r}) + pd.Timedelta(days=1))]['{col}'].sum())\n"
        f"_b = float({var}[({var}['_date'] >= pd.Timestamp({start2!r})) & ({var}['_date'] < pd.Timestamp({end2!r}) + pd.Timedelta(days=1))]['{col}'].sum())\n"
        "RESULT = f'{round((_b - _a) / _a * 100, 2):.2f}%' if _a else '0.00%'\n"
    )
    return code


def cand_pct_change_mtd(asof, use_lines=False):
    a = pd.Timestamp(asof)
    if a.month > 1:
        py, pm = a.year, a.month - 1
    else:
        py, pm = a.year - 1, 12
    prev_last = (pd.Timestamp(py, pm, 1) + pd.offsets.MonthEnd(0)).day
    prev_end = pd.Timestamp(py, pm, min(a.day, prev_last))
    return cand_pct_change_periods(
        pd.Timestamp(py, pm, 1).date().isoformat(), prev_end.date().isoformat(),
        a.replace(day=1).date().isoformat(), a.date().isoformat(),
        by="revenue", use_lines=use_lines,
    )


def cand_pct_change(y1, m1, y2, m2, use_lines=False):
    table = "lines" if use_lines else "orders"
    var = "_l" if use_lines else "_o"
    code = f"{var} = {table}[~{table}['_bad']].copy()\n"
    code += f"{var}['_y'] = {var}['_date'].dt.year\n{var}['_mo'] = {var}['_date'].dt.month\n"
    code += (
        f"_a = float({var}[( {var}['_y'] == {y1}) & ({var}['_mo'] == {m1})]['_revenue'].sum())\n"
        f"_b = float({var}[( {var}['_y'] == {y2}) & ({var}['_mo'] == {m2})]['_revenue'].sum())\n"
        "RESULT = f'{round((_b - _a) / _a * 100, 2):.2f}%' if _a else '0.00%'\n"
    )
    return code


def cand_pct_change_na(y1, m1, y2, m2):
    table = "lines" if False else "orders"
    code = "".join([
        "_o = orders[~orders['_bad']].copy()\n",
        "_o['_y'] = _o['_date'].dt.year\n_o['_mo'] = _o['_date'].dt.month\n",
        f"_a = float(_o[(_o['_y'] == {y1}) & (_o['_mo'] == {m1})]['_revenue'].sum())\n",
        f"_b = float(_o[(_o['_y'] == {y2}) & (_o['_mo'] == {m2})]['_revenue'].sum())\n",
        "RESULT = 'unanswerable' if _a == 0 else f'{round((_b - _a) / _a * 100, 2):.2f}%'\n",
    ])
    return code


def cand_trend(years_months, use_lines=False):
    table = "lines" if use_lines else "orders"
    var = "_l" if use_lines else "_o"
    code = f"{var} = {table}[~{table}['_bad']].copy()\n"
    code += f"{var}['_y'] = {var}['_date'].dt.year\n{var}['_mo'] = {var}['_date'].dt.month\n"
    vals = []
    for (y, m) in years_months:
        vals.append(f"float({var}[({var}['_y'] == {y}) & ({var}['_mo'] == {m})]['_revenue'].sum())")
    code += "_v = [" + ", ".join(vals) + "]\n"
    code += "RESULT = bool(all(_v[i] < _v[i + 1] for i in range(len(_v) - 1)))\n"
    return code


def cand_best_month(months, use_lines=False, mode="max"):
    table = "lines" if use_lines else "orders"
    var = "_l" if use_lines else "_o"
    code = f"{var} = {table}[~{table}['_bad']].copy()\n"
    code += f"{var}['_y'] = {var}['_date'].dt.year\n{var}['_mo'] = {var}['_date'].dt.month\n"
    pairs = ", ".join(f"({y}, {m})" for y, m in months)
    code += f"_months = [{pairs}]\n"
    code += (
        f"_vals = {{(y, m): float({var}[({var}['_y'] == y) & ({var}['_mo'] == m)]['_revenue'].sum()) for y, m in _months}}\n"
    )
    if mode == "max":
        code += "_best = max(_vals, key=_vals.get)\n"
    else:
        code += "_best = min(_vals, key=_vals.get)\n"
    code += "RESULT = f'{_best[0]:04d}-{_best[1]:02d}'\n"
    return code


def _top_agg_code(n=3, by="qty_base", tie_name=False, one=False):
    code = "_l = _l.copy()\n"
    code += "_l['_k'] = _l['_product'].map(normalize_text)\n"
    code += "_dm = _l.groupby(['_k', '_product']).size().reset_index(name='_c').sort_values('_c', ascending=False).drop_duplicates('_k').set_index('_k')['_product'].to_dict()\n"
    if by == "count":
        code += "_g = _l.groupby('_k')['_oid'].nunique()\n"
    else:
        col = {"qty_base": "_qty_base", "qty": "_qty", "revenue": "_revenue"}[by]
        code += f"_g = _l.groupby('_k')['{col}'].sum()\n"
    if one:
        code += "_g = _g.sort_values(ascending=False)\n"
        code += "RESULT = str(_dm.get(_g.index[0], _g.index[0])) if len(_g) else 'unanswerable'\n"
    elif tie_name:
        code += "_df = pd.DataFrame({'v': list(_g.values), 'n': [_dm.get(k, k) for k in _g.index]})\n"
        code += "_df = _df.sort_values(['v', 'n'], ascending=[False, True])\n"
        code += f"RESULT = [str(x) for x in _df['n'].head({n})]\n"
    else:
        code += "_g = _g.sort_values(ascending=False)\n"
        code += f"RESULT = [str(_dm.get(k, k)) for k in _g.index[:{n}]]\n"
    return code


def cand_top_products(span, n=3, by="qty_base", use_lines=True):
    code = _head("lines", span, True, "_l")
    code += _top_agg_code(n, by)
    return code


def cand_top_product_one(span, by="qty_base"):
    code = _head("lines", span, True, "_l")
    code += _top_agg_code(1, by, one=True)
    return code


def cand_top_customers(span, n=3, by="revenue", tie_name=False):
    code = _head("orders", span, True, "_o")
    code += "_o = _o[~_o['_customer'].map(normalize_text).isin(" + repr(sorted(WALKIN)) + ")]\n"
    code += "_g = _o.groupby('_customer')['_revenue'].sum()\n"
    code += "_g = _g[_g > 0].sort_values(ascending=False)\n"
    code += "_nm = customers.drop_duplicates('_cid').set_index('_cid')['_cname'].to_dict() if len(customers) else {}\n"
    code += "_names = [_re.sub(r'\\s*-\\s*[\\d\\s\\.]{8,}$', '', _re.sub(r'\\s*\\([^)]*\\)\\s*$', '', str(_nm.get(str(x), str(x))))) for x in _g.index]\n"
    if tie_name:
        code += "_df = pd.DataFrame({'v': list(_g.values), 'n': _names})\n"
        code += "_df = _df.sort_values(['v', 'n'], ascending=[False, True])\n"
        code += f"RESULT = list(_df['n'].head({n}))\n"
    else:
        code += f"RESULT = _names[:{n}]\n"
    return code


def cand_top_customer_one(span, tie_name=False):
    code = _head("orders", span, True, "_o")
    code += "_o = _o[~_o['_customer'].map(normalize_text).isin(" + repr(sorted(WALKIN)) + ")]\n"
    code += "_g = _o.groupby('_customer')['_revenue'].sum()\n"
    code += "_g = _g[_g > 0].sort_values(ascending=False)\n"
    code += "_nm = customers.drop_duplicates('_cid').set_index('_cid')['_cname'].to_dict() if len(customers) else {}\n"
    code += "_v = str(_nm.get(str(_g.index[0]), _g.index[0])) if len(_g) else 'unanswerable'\n"
    code += "RESULT = _re.sub(r'\\s*-\\s*[\\d\\s\\.]{8,}$', '', _re.sub(r'\\s*\\([^)]*\\)\\s*$', '', _v))\n"
    return code


def cand_best_staff(span, use_name=False):
    code = _head("orders", span, True, "_o")
    code += "_g = _o.groupby('_staff')['_revenue'].sum().sort_values(ascending=False)\n"
    if use_name:
        code += "RESULT = str(_o[_o['_staff'] == _g.index[0]]['_staff_name'].iloc[0]) if len(_g) else 'unanswerable'\n"
    else:
        code += "RESULT = str(_g.index[0]) if len(_g) else 'unanswerable'\n"
    return code


def cand_best_customer_orders(span, use_name=True):
    code = _head("orders", span, True, "_o")
    code += "_o = _o[~_o['_customer'].map(normalize_text).isin(" + repr(sorted(WALKIN)) + ")]\n"
    code += "_g = _o.groupby('_customer')['_oid'].nunique()\n"
    code += "_g = _g.sort_values(ascending=False)\n"
    code += "_nm = customers.drop_duplicates('_cid').set_index('_cid')['_cname'].to_dict() if len(customers) else {}\n"
    code += "_v = str(_nm.get(str(_g.index[0]), _g.index[0])) if len(_g) else 'unanswerable'\n"
    code += "RESULT = _re.sub(r'\\s*-\\s*[\\d\\s\\.]{8,}$', '', _re.sub(r'\\s*\\([^)]*\\)\\s*$', '', _v))\n"
    return code


def cand_month_list(months, use_lines=False):
    """Revenue for an explicit ordered list of (y, m) months."""
    code = _head("lines" if use_lines else "orders", None, True, "_l" if use_lines else "_o")
    v = "_l" if use_lines else "_o"
    code += f"{v}['_y'] = {v}['_date'].dt.year\n"
    code += f"{v}['_mo'] = {v}['_date'].dt.month\n"
    code += f"_s = {v}.groupby(['_y', '_mo'])['_revenue'].sum()\n"
    parts = ", ".join(f"int(round(float(_s.get(({y}, {m}), 0))))" for (y, m) in months)
    code += f"RESULT = [{parts}]\n"
    return code


def cand_top_products_tie(span, n=3, by="qty_base", name_tie=True):
    code = _head("lines", span, True, "_l")
    code += _top_agg_code(n, by, tie_name=True, one=(n == 1))
    return code


def cand_share(span, cat_match=None, product_match=None, by="revenue"):
    code = _head("lines", span, True, "_l")
    if by == "revenue":
        code += "_all = float(_l['_revenue'].sum())\n"
    else:
        code += "_all = float(_l['_qty_base'].sum())\n"
    if product_match:
        code += f"_l = _l[_l['_product'].map(normalize_text) == {product_match!r}]\n"
    elif cat_match:
        code += f"_l = _l[_l['_category'].map(normalize_text) == {cat_match!r}]\n"
    col = "_revenue" if by == "revenue" else "_qty_base"
    code += (
        f"_part = float(_l['{col}'].sum())\n"
        "RESULT = f'{round(_part / _all * 100, 2):.2f}%' if _all else '0.00%'\n"
    )
    return code


def cand_days_above(span, threshold, use_lines=False):
    table = "lines" if use_lines else "orders"
    var = "_l" if use_lines else "_o"
    code = _head(table, span, True, var)
    code += (
        f"_g = {var}.groupby({var}['_date'].dt.date)['_revenue'].sum()\n"
        f"RESULT = int((_g >= {threshold}).sum())\n"
    )
    return code


def cand_orders_above(span, threshold, bad=True):
    code = _head("orders", span, bad, "_o")
    code += f"RESULT = int((_o['_revenue'] >= {threshold}).sum())\n"
    return code


def cand_orders_above_lines(span, threshold):
    code = _head("lines", span, True, "_l")
    code += "_g = _l.groupby('_oid')['_revenue'].sum()\n"
    code += f"RESULT = int((_g >= {threshold}).sum())\n"
    return code


def cand_share_channel(span, channel):
    code = _head("orders", span, True, "_o")
    code += "_all = float(_o['_revenue'].sum())\n"
    code += f"_part = float(_o[_o['_channel'].map(normalize_text) == {channel!r}]['_revenue'].sum())\n"
    code += "RESULT = f'{round(_part / _all * 100, 2):.2f}%' if _all else '0.00%'\n"
    return code


def cand_stock_value():
    code = "RESULT = 'unanswerable'\n"
    code += "if len(stock) and len(products):\n"
    code += "    _pp = products.copy()\n"
    code += "    _pp['_k'] = _pp['_product'].map(normalize_text)\n"
    code += "    _c = _pp.drop_duplicates('_k').set_index('_k')['_cost'].to_dict()\n"
    code += "    _pk = products.assign(_k=products['_pkey'].map(normalize_text)).drop_duplicates('_k').set_index('_k')['_cost'].to_dict()\n"
    code += "    _v = 0.0\n"
    code += "    for _p, _q in zip(stock['_product'], stock['_stock']):\n"
    code += "        _k = normalize_text(_p)\n"
    code += "        _cc = _c.get(_k, _pk.get(_k, float('nan')))\n"
    code += "        if _cc == _cc:\n"
    code += "            _v += float(_q) * float(_cc)\n"
    code += "    RESULT = int(round(_v))\n"
    return code


def cand_products_min_orders(span, n):
    code = _head("lines", span, True, "_l")
    code += (
        "_g = _l.groupby('_product')['_oid'].nunique()\n"
        f"RESULT = int((_g >= {n}).sum())\n"
    )
    return code


def cand_customers_min_orders(span, n, percent=False):
    code = _head("orders", span, True, "_o")
    code += "_o = _o.copy()\n"
    code += "_o['_ck'] = _o['_customer'].map(normalize_text)\n"
    code += "_o = _o[~_o['_ck'].isin(" + repr(sorted(WALKIN)) + ")]\n"
    code += (
        "_g = _o.groupby('_ck')['_oid'].nunique()\n"
        f"_k = int((_g >= {n}).sum())\n"
        "_t = int(_g.shape[0])\n"
    )
    if percent:
        code += "RESULT = f'{round(_k / _t * 100, 2):.2f}%' if _t else '0.00%'\n"
    else:
        code += "RESULT = _k\n"
    return code


def cand_debt_sum(span, exclude_cod_cancel=True):
    code = _head("orders", span, False, "_o")
    if exclude_cod_cancel:
        code += (
            "_o = _o[~_o['_status'].astype(str).str.contains('cancel|huy|huỷ', case=False, na=False)]\n"
            "_o = _o[~_o['_payment'].astype(str).str.contains('cod', case=False, na=False)]\n"
        )
    code += "RESULT = int(round(float(_o['_debt'].sum())))\n"
    return code


def cand_debt_customers(span):
    code = _head("orders", span, False, "_o")
    code += (
        "_o = _o[~_o['_status'].astype(str).str.contains('cancel|huy', case=False, na=False)]\n"
        "_g = _o.groupby('_customer')['_debt'].sum()\n"
        "RESULT = int((_g > 0).sum())\n"
    )
    return code


def cand_debt_top(span, n=5):
    code = _head("orders", span, False, "_o")
    code += (
        "_o = _o[~_o['_status'].astype(str).str.contains('cancel|huy', case=False, na=False)]\n"
        "_o = _o[~_o['_payment'].astype(str).str.contains('cod', case=False, na=False)]\n"
        "_g = _o.groupby('_customer')['_debt'].sum()\n"
        "_g = _g[_g > 0].sort_values(ascending=False)\n"
        f"_top = _g.head({n})\n"
        "RESULT = {'columns': ['khach_hang', 'so_tien_no'], 'rows': [[str(k), int(round(v))] for k, v in _top.items()]}\n"
    )
    return code


def cand_stock_sum(product_match=None):
    if product_match:
        code = f"_s = stock[stock['_product'].map(normalize_text) == {product_match!r}]\n"
    else:
        code = "_s = stock\n"
    code += "RESULT = int(round(float(_s['_stock'].sum())))\n"
    return code


def cand_purchase_sum(span):
    code = "_p = purchases.copy()\n"
    if span and (span.get("start") or span.get("end")):
        code += f"_p = {span_filter('_p', span)}\n"
    code += "RESULT = int(round(float(_p['_amount'].sum())))\n"
    return code


def cand_purchase_avg(span, product_match=None, unit=None):
    code = "_p = purchase_lines.copy() if len(purchase_lines) else purchases.copy()\n"
    if span and (span.get("start") or span.get("end")):
        code += f"_p = {span_filter('_p', span)}\n"
    if product_match:
        code += "_nm = _p['_pname'] if '_pname' in _p.columns else _p['_product']\n"
        code += f"_m = _nm.map(normalize_text) == {product_match!r}\n"
        code += f"if not _m.any():\n    _m = _nm.map(normalize_text).str.contains({product_match!r}, na=False)\n"
        code += "_p = _p[_m]\n"
    if unit:
        code += (
            f"if '_unit' in _p.columns:\n"
            f"    _u = _p[_p['_unit'].map(normalize_text) == {unit!r}]\n"
            "    if len(_u):\n        _p = _u\n"
        )
    code += "RESULT = int(round(float(_p['_amount'].sum() / _p['_qty'].sum()))) if _p['_qty'].sum() else 'unanswerable'\n"
    return code


def cand_stock_parts(product_match, ratio=1, asof=None):
    ratio = max(int(ratio or 1), 1)
    code = f"_nm = {product_match!r}\n_r = {ratio}\n_v = None\n"
    code += "if len(stock):\n"
    code += "    _s = stock[stock['_product'].map(normalize_text).str.contains(_nm, na=False)]\n"
    code += "    if len(_s):\n        _v = float(_s['_stock'].sum())\n"
    code += "if _v is None and len(lots):\n"
    if asof:
        code += f"    _A = pd.Timestamp({asof!r})\n"
    else:
        code += "    _A = pd.Timestamp.today().normalize()\n"
    code += "    _ln = lots['_pname'] if '_pname' in lots.columns else lots['_product']\n"
    code += "    _lt = lots[_ln.map(normalize_text).str.contains(_nm, na=False)]\n"
    code += "    if '_date' in _lt.columns:\n        _lt = _lt[_lt['_date'] <= _A]\n"
    code += "    _sold = lot_sales.groupby('_lot')['_qty'].sum().to_dict() if len(lot_sales) else {}\n"
    code += "    _v = float((_lt['_qty'] - _lt['_lot'].map(lambda x: _sold.get(str(x), 0))).clip(lower=0).sum())\n"
    code += "RESULT = [int(_v // _r), int(_v % _r)] if _v is not None else 'unanswerable'\n"
    return code


def cand_lot_expiry(product_match, asof):
    code = f"_A = pd.Timestamp({asof!r})\n"
    code += "_lt = lots.copy()\n"
    code += "_sold = lot_sales.groupby('_lot')['_qty'].sum().to_dict() if len(lot_sales) else {}\n"
    code += "_lt['_rem'] = _lt['_qty'] - _lt['_lot'].map(lambda x: _sold.get(str(x), 0))\n"
    code += "_lt = _lt[_lt['_rem'] > 0]\n"
    code += "if '_date' in _lt.columns:\n    _lt = _lt[_lt['_date'] <= _A]\n"
    code += "_ln = _lt['_pname'] if '_pname' in _lt.columns else _lt['_product']\n"
    code += f"_lt = _lt[_ln.map(normalize_text).str.contains({product_match!r}, na=False)]\n"
    code += "_lt = _lt.dropna(subset=['_expiry']).sort_values('_expiry')\n"
    code += "RESULT = _lt['_expiry'].iloc[0].date().isoformat() if len(_lt) else 'unanswerable'\n"
    return code


def cand_lot_expiring_value(start, end, asof):
    code = f"_A = pd.Timestamp({asof!r})\n"
    code += "_lt = lots.copy()\n"
    code += "_sold = lot_sales.groupby('_lot')['_qty'].sum().to_dict() if len(lot_sales) else {}\n"
    code += "_lt['_rem'] = _lt['_qty'] - _lt['_lot'].map(lambda x: _sold.get(str(x), 0))\n"
    code += "_lt = _lt[_lt['_rem'] > 0]\n"
    code += "if '_date' in _lt.columns:\n    _lt = _lt[_lt['_date'] <= _A]\n"
    code += f"_lt = _lt[(_lt['_expiry'] >= pd.Timestamp({start!r})) & (_lt['_expiry'] <= pd.Timestamp({end!r}))]\n"
    code += "RESULT = int(round(float((_lt['_rem'] * _lt['_price']).sum())))\n"
    return code


def cand_delivery_count(span):
    code = "_d = deliveries.copy()\n"
    if span and (span.get("start") or span.get("end")):
        code += f"_d = {span_filter('_d', span)}\n"
    code += "RESULT = int(_d.drop_duplicates(['_oid', '_line']).shape[0]) if len(_d) else 0\n"
    return code


def _debt_available(frames):
    """True when the canonical model carries any payment / debt information."""
    p = frames.get("payments")
    if p is not None and len(p):
        return True
    o = frames.get("orders")
    if o is None or not len(o):
        return False
    if "_debt" in o.columns and float(pd.to_numeric(o["_debt"], errors="coerce").fillna(0).abs().sum()) > 0:
        return True
    if "_payment" in o.columns and o["_payment"].astype(str).str.strip().ne("").any():
        return True
    if "_paid" in o.columns and "_revenue" in o.columns:
        _diff = (pd.to_numeric(o["_paid"], errors="coerce").fillna(0)
                 - pd.to_numeric(o["_revenue"], errors="coerce").fillna(0))
        if _diff.abs().gt(0).any():
            return True
    return False


def cand_debt_paid(span):
    code = "_p = payments.copy()\n"
    if span and (span.get("start") or span.get("end")):
        code += f"_p = {span_filter('_p', span)}\n"
    code += "_od = orders.drop_duplicates('_oid').set_index('_oid')\n"
    code += "_p = _p[_p['_oid'].isin(_od.index)].copy()\n"
    code += "_p['_odate'] = pd.to_datetime(_p['_oid'].map(_od['_date']), errors='coerce')\n"
    code += "_p['_omethod'] = _p['_oid'].map(_od['_payment']).astype(str)\n"
    code += "_p = _p[_p['_omethod'].map(normalize_text).str.contains('no|debt', na=False)]\n"
    code += "_p = _p[_p['_date'] > _p['_odate'] + pd.Timedelta(days=1)]\n"
    code += "RESULT = int(round(float(_p['_amount'].sum())))\n"
    return code


def cand_debt_pair(span, cust_name):
    code = _head("orders", span, True, "_o")
    code += "_nm = customers.drop_duplicates('_cid').set_index('_cid')['_cname'].to_dict() if len(customers) else {}\n"
    code += f"_CUST = {cust_name!r}\n"
    code += "def _cn(x):\n    return normalize_text(_nm.get(str(x), str(x)))\n"
    code += "_oc = _o[_o['_customer'].map(_cn) == _CUST]\n"
    code += "_oc = _oc[_oc['_payment'].map(normalize_text).str.contains('no|debt', na=False)]\n"
    code += "_same = payments.copy()\n"
    code += "_same = _same[_same['_oid'].isin(_oc['_oid'])] if len(_same) else _same\n"
    code += "_samepay = 0.0\n"
    code += "if len(_same):\n"
    code += "    _od0 = orders.drop_duplicates('_oid').set_index('_oid')\n"
    code += "    _same['_odate'] = pd.to_datetime(_same['_oid'].map(_od0['_date']), errors='coerce')\n"
    code += "    _same = _same[_same['_date'].dt.normalize() <= _same['_odate'].dt.normalize()]\n"
    code += "    _samepay = float(_same['_amount'].sum())\n"
    code += "_add = float(_oc['_total'].sum()) - _samepay\n"
    code += "_p = payments.copy()\n"
    if span and (span.get("start") or span.get("end")):
        code += f"_p = {span_filter('_p', span)}\n"
    code += "_od = orders.drop_duplicates('_oid').set_index('_oid')\n"
    code += "_p = _p[_p['_oid'].isin(_od.index)].copy()\n"
    code += "_p['_odate'] = pd.to_datetime(_p['_oid'].map(_od['_date']), errors='coerce')\n"
    code += "_p['_omethod'] = _p['_oid'].map(_od['_payment']).astype(str)\n"
    code += "_p['_ocust'] = _p['_oid'].map(_od['_customer']).astype(str)\n"
    code += "_p = _p[_p['_ocust'].map(_cn) == _CUST]\n"
    code += "_p = _p[_p['_omethod'].map(normalize_text).str.contains('no|debt', na=False)]\n"
    code += "_p = _p[_p['_date'] > _p['_odate'] + pd.Timedelta(days=1)]\n"
    code += "RESULT = [int(round(_add)), int(round(float(_p['_amount'].sum())))]\n"
    return code


def cand_shift_pct(span):
    code = _head("lines", span, True, "_l")
    code += "_g = _l.groupby('_shift')['_revenue'].sum()\n"
    code += "_s = float(_g.get('sang', 0)); _c = float(_g.get('chieu', 0))\n"
    code += "RESULT = f'{round((_c - _s) / _s * 100, 2):.2f}%' if _s else '0.00%'\n"
    return code


def cand_channel_rev(span, chan):
    code = _head("lines", span, True, "_l")
    code += f"RESULT = int(round(float(_l[_l['_channel'].map(normalize_text).str.contains({chan!r}, na=False)]['_revenue'].sum())))\n"
    return code


def cand_channel_share(span, chan):
    code = _head("lines", span, True, "_l")
    code += "_all = float(_l['_revenue'].sum())\n"
    code += f"_part = float(_l[_l['_channel'].map(normalize_text).str.contains({chan!r}, na=False)]['_revenue'].sum())\n"
    code += "RESULT = f'{round(_part / _all * 100, 2):.2f}%' if _all else '0.00%'\n"
    return code


def cand_channel_list(span, chans):
    code = _head("lines", span, True, "_l")
    code += f"_vals = {list(chans)!r}\n"
    code += "RESULT = [int(round(float(_l[_l['_channel'].map(normalize_text).str.contains(v, na=False)]['_revenue'].sum()))) for v in _vals]\n"
    return code


def cand_rx_metric(span, mode="rev_true"):
    code = _head("lines", span, True, "_l")
    if mode == "rev_true":
        code += "RESULT = int(round(float(_l[_l['_rx']]['_revenue'].sum())))\n"
    elif mode == "rev_false":
        code += "RESULT = int(round(float(_l[~_l['_rx'].astype(bool)]['_revenue'].sum())))\n"
    elif mode == "qty_true":
        code += "RESULT = int(round(float(_l[_l['_rx']]['_qty_base'].sum())))\n"
    elif mode == "share_true":
        code += "_all = float(_l['_revenue'].sum())\n"
        code += "_part = float(_l[_l['_rx']]['_revenue'].sum())\n"
        code += "RESULT = f'{round(_part / _all * 100, 2):.2f}%' if _all else '0.00%'\n"
    return code


def cand_supplier_top(span):
    code = "_p = purchases.copy()\n"
    if span and (span.get("start") or span.get("end")):
        code += f"_p = {span_filter('_p', span)}\n"
    code += "_p = _p[_p['_supplier'].astype(str).str.strip().ne('') & _p['_supplier'].astype(str).ne('nan')]\n"
    code += "_g = _p.groupby('_supplier')['_amount'].sum().sort_values(ascending=False)\n"
    code += "RESULT = str(_g.index[0]) if len(_g) else 'unanswerable'\n"
    return code


def cand_gross_profit(span):
    code = _head("lines", span, True, "_l")
    code += "RESULT = int(round(float((_l['_revenue'] - _l['_qty'] * _l['_cost']).sum())))\n"
    return code


def cand_zero_sales(span):
    code = "_l = lines[~lines['_bad']].copy()\n"
    start = span.get("start") if span else None
    end = span.get("end") if span else None
    if start is not None:
        code += f"_prev = _l[_l['_date'] < pd.Timestamp({start!r})]\n"
        code += "_all = set(_prev['_product'].map(normalize_text))\n"
    else:
        code += "_all = set(_l['_product'].map(normalize_text))\n"
    if span and (span.get("start") or span.get("end")):
        code += f"_l = {span_filter('_l', span)}\n"
    code += "_sold = set(_l['_product'].map(normalize_text))\n"
    code += "RESULT = int(len(_all - _sold))\n"
    return code


def cand_price_at(product_match, date):
    code = (
        f"_ph = price_history[price_history['_product'].map(normalize_text) == {product_match!r}]\n"
        f"_ph = _ph[_ph['_date'] <= pd.Timestamp({date!r})].sort_values('_date')\n"
        "RESULT = int(round(float(_ph['_new_price'].iloc[-1]))) if len(_ph) else 'unanswerable'\n"
    )
    return code


def cand_metric_dim(span, dim_col, dim_val, metric="revenue", use_lines=True, contains=False,
                    staff_name=None, tie_name=False):
    table = "lines" if use_lines else "orders"
    var = "_l" if use_lines else "_o"
    code = _head(table, span, True, var)
    if metric == "share":
        code += f"_all = float({var}['_revenue'].sum())\n"
    if dim_col == "_staff":
        conds = [f"{var}['_staff'].map(normalize_text) == {norm_name(dim_val)!r}"]
        if staff_name:
            conds.append(
                f"{var}['_staff_name'].map(normalize_text).str.contains({norm_name(staff_name)!r}, na=False)"
            )
        code += f"{var} = {var}[(" + ") | (".join(conds) + ")]\n"
    elif contains:
        code += f"{var} = {var}[{var}['{dim_col}'].map(normalize_text).str.contains({dim_val!r}, na=False)]\n"
    else:
        code += f"{var} = {var}[{var}['{dim_col}'].map(normalize_text) == {dim_val!r}]\n"
    if metric == "revenue":
        code += f"RESULT = {_num(var + chr(91) + chr(39) + '_revenue' + chr(39) + chr(93) + '.sum()')}\n"
    elif metric == "qty_base":
        code += f"RESULT = int(round(float({var}['_qty_base'].sum())))\n"
    elif metric == "qty":
        code += f"RESULT = int(round(float({var}['_qty'].sum())))\n"
    elif metric == "orders":
        code += f"RESULT = int({var}['_oid'].nunique())\n"
    elif metric == "share":
        code += "_part = float(" + var + "['_revenue'].sum())\n"
        code += "RESULT = f'{round(_part / _all * 100, 2):.2f}%' if _all else '0.00%'\n"
    return code


def cand_revenue_ingr(span, ingr, metric="revenue", contains_only=False):
    code = _head("lines", span, True, "_l")
    code += f"_m1 = _l['_ingredient'].map(normalize_text) == {ingr!r}\n"
    code += f"_m2 = _l['_product'].map(normalize_text).str.contains({ingr!r}, na=False)\n"
    if contains_only:
        code += "_l = _l[_m2]\n"
    else:
        code += "_m0 = _l['_ingredient'].astype(str).str.strip().eq('')\n"
        code += "if _m1.any():\n    _l = _l[_m1]\nelse:\n    _l = _l[_m0 & _m2]\n"
    if metric == "revenue":
        code += f"RESULT = {_num('_l' + chr(91) + chr(39) + '_revenue' + chr(39) + chr(93) + '.sum()')}\n"
    elif metric == "qty_base":
        code += "RESULT = int(round(float(_l['_qty_base'].sum())))\n"
    elif metric == "qty":
        code += "RESULT = int(round(float(_l['_qty'].sum())))\n"
    return code


def _debt_code(span, asof):
    end = span.get("end") if span else None
    X = (pd.Timestamp(end) if end else pd.Timestamp(asof)) + pd.Timedelta(days=1)
    code = f"X = pd.Timestamp({X.date().isoformat()!r})\n"
    code += "_o = orders.copy()\n"
    code += "_o = _o[_o['_date'] < X]\n"
    code += "_o = _o[~_o['_bad']]\n"
    code += "_mn = _o['_payment'].astype(str).map(normalize_text)\n"
    code += "_o = _o[~_mn.str.contains('cod|thu ho', na=False)]\n"
    code += "_code = _o['_custcode'].astype(str).str.strip() if '_custcode' in _o.columns else pd.Series([''] * len(_o), index=_o.index)\n"
    code += "_code = _code.where(~_code.isin(['', 'nan', 'None', 'NaN']), '')\n"
    code += "_nm = customers.drop_duplicates('_cid').set_index('_cid')['_cname'].to_dict() if len(customers) else {}\n"
    code += "_raw = _o['_customer'].astype(str)\n"
    code += "_is_code_col = bool(_raw.str.match(r'^[A-Za-z]{0,5}\\d{2,}$').mean() > 0.5)\n"
    code += "_o['_cname'] = [str(_nm.get(str(c), '')) or str(_nm.get(str(n), n)) for c, n in zip(_code, _raw)]\n"
    code += "_o['_ckey'] = [str(c) if str(c) else (str(n) if _is_code_col else normalize_text(n)) for c, n in zip(_code, _raw)]\n"
    code += "_has_debt = '_debt' in _o.columns and float(_o['_debt'].fillna(0).abs().sum()) > 0\n"
    code += "if _has_debt:\n"
    code += "    _o['_debtX'] = _o['_debt'].fillna(0).clip(lower=0)\n"
    code += "elif len(payments):\n"
    code += "    _pp = payments[payments['_date'] < X].groupby('_oid')['_amount'].sum()\n"
    code += "    _o['_debtX'] = (_o['_total'] - _o['_oid'].map(_pp).fillna(0)).clip(lower=0)\n"
    code += "else:\n"
    code += "    _o['_debtX'] = (_o['_total'] - _o['_paid'].fillna(0)).clip(lower=0)\n"
    return code


def cand_debt_at_sum(span, asof, min_age=None):
    code = _debt_code(span, asof)
    if min_age is not None:
        code += f"_age = (X - pd.Timedelta(days=1) - _o['_date']).dt.days\n"
        code += f"_o = _o[_age > {int(min_age)}]\n"
    return code + "RESULT = int(round(float(_o['_debtX'].sum())))\n"


def cand_debt_at_customers(span, asof):
    code = _debt_code(span, asof)
    code += "_o = _o[~_o['_cname'].map(normalize_text).isin(" + repr(sorted(WALKIN)) + ")]\n"
    code += "_o = _o[_o['_ckey'].astype(str).ne('')]\n"
    code += "_g = _o.groupby('_ckey')['_debtX'].sum()\n"
    code += "RESULT = int((_g > 0).sum())\n"
    return code


def cand_debt_at_top(span, asof, n=5):
    code = _debt_code(span, asof)
    code += "_o = _o[~_o['_cname'].map(normalize_text).isin(" + repr(sorted(WALKIN)) + ")]\n"
    code += "_o = _o[_o['_ckey'].astype(str).ne('')]\n"
    code += "_g = _o.groupby('_ckey').agg(_d=('_debtX', 'sum'), _n=('_cname', 'first'))\n"
    code += "_g = _g[_g['_d'] > 0].sort_values('_d', ascending=False)\n"
    code += f"_top = _g.head({n})\n"
    code += "RESULT = {'columns': ['khach_hang', 'so_tien_no'], 'rows': [[str(r['_n']), int(round(r['_d']))] for _, r in _top.iterrows()]}\n"
    return code


def cand_debt_age_buckets(span, asof):
    code = _debt_code(span, asof)
    code += "_age = (X - pd.Timedelta(days=1) - _o['_date']).dt.days\n"
    code += "RESULT = [int(round(float(_o['_debtX'][_age <= 7].sum()))), int(round(float(_o['_debtX'][(_age > 7) & (_age <= 15)].sum()))), int(round(float(_o['_debtX'][_age > 15].sum())))]\n"
    return code


def cand_debt_static_customers(span):
    code = _head("orders", span, False, "_o")
    code += "_o = _o[~_o['_status'].astype(str).str.contains('cancel|huy', case=False, na=False)]\n"
    code += "_o = _o[~_o['_payment'].astype(str).str.contains('cod', case=False, na=False)]\n"
    code += "_nm = customers.drop_duplicates('_cid').set_index('_cid')['_cname'].to_dict() if len(customers) else {}\n"
    code += "_o['_cname'] = _o['_customer'].map(lambda x: _nm.get(str(x), str(x)))\n"
    code += "_o = _o[~_o['_cname'].map(normalize_text).isin(" + repr(sorted(WALKIN)) + ")]\n"
    code += "_g = _o.groupby('_cname')['_debt'].sum()\n"
    code += "RESULT = int((_g > 0).sum())\n"
    return code


# ---------------------------------------------------------------------------
# product / category / unit / threshold extraction
# ---------------------------------------------------------------------------
GLOBAL_CTX: dict = {}


def build_match_lists(frames):
    prods = []
    try:
        for v in frames["lines"]["_product"].dropna().unique():
            n = norm_name(v)
            if len(n) >= 4:
                prods.append((n, str(v)))
    except Exception:
        pass
    try:
        for v in frames["products"]["_product"].dropna().unique():
            n = norm_name(v)
            if len(n) >= 4:
                prods.append((n, str(v)))
    except Exception:
        pass
    prods = sorted(set(prods), key=lambda t: -len(t[0]))

    cats = []
    try:
        for v in frames["lines"]["_category"].dropna().unique():
            n = norm_name(v)
            if len(n) >= 3:
                cats.append((n, str(v)))
    except Exception:
        pass
    cats = sorted(set(cats), key=lambda t: -len(t[0]))
    return prods, cats


def find_in_text(qn, pairs):
    """Longest normalized name contained in the question."""
    qnn = norm_name(qn)
    best = None
    for n, raw in pairs:
        if n and n in qnn:
            if best is None or len(n) > len(best[0]):
                best = (n, raw)
    return best


UNITS = ["kg", "lon", "chai", "hop", "goi", "thung", "loc", "ly", "cai", "phan", "dia",
         "suat", "vi", "vien", "bo", "cuon", "chiec", "hop", "tui", "bao", "met", "lit", "ml"]


def find_unit(qn):
    for u in UNITS:
        if re.search(r"\b" + u + r"\b", qn):
            return u
    return None


CHANNEL_ALIASES = [
    (r"d+ienj?\s*thoai|d+thoai|dien thoi|phone|goi dien|qua dien thoai", "phone"),
    (r"zalo", "zalo"),
    (r"tai quay|\bquay\b|store|truc tiep|tai cua hang|ban tai cua hang", "store"),
]


def find_channel(qn):
    for pat, val in CHANNEL_ALIASES:
        if re.search(pat, qn):
            return val
    return None


def find_channels_all(qn):
    found = []
    for pat, val in CHANNEL_ALIASES:
        m = re.search(pat, qn)
        if m:
            found.append((m.start(), val))
    found.sort()
    out = []
    for _, v in found:
        if v not in out:
            out.append(v)
    return out


def conv_ratio(frames, product_match):
    cv = frames.get("conversions")
    if cv is None or not len(cv):
        return 1
    try:
        m = cv[cv["_pname"].map(norm_name).str.contains(product_match, na=False)]
        if len(m):
            r = pd.to_numeric(m["_ratio"], errors="coerce").dropna()
            if len(r):
                return int(r.max())
    except Exception:
        pass
    return 1


def find_customer(qn, frames):
    c = frames.get("customers")
    if c is None or not len(c) or "_cname" not in c.columns:
        return None
    pairs = [(norm_name(v), v) for v in _unique_norm(c["_cname"])]
    pairs = [p for p in pairs if len(p[0]) >= 4]
    return find_in_text(qn, pairs)


def find_unit_outside(qn, prod_norm=None, qraw=None):
    """First unit token in the question that is NOT inside the product name."""
    text = qn
    if prod_norm and prod_norm not in text and qraw is not None:
        text = norm_name(qraw)
    spans = []
    if prod_norm:
        i = text.find(prod_norm)
        if i >= 0:
            spans.append((i, i + len(prod_norm)))
    bad_next = {"bao": r"\s*nhieu", "phan": r"\s*tram", "dia": r"\s*chi",
                "cai": r"\s*(gi|nay|do|kia)", "chiec": r"\s*(gi|nay|do|kia)",
                "vi": r"\s*du", "bo": r"\s*(qua|phan)", "met": r"\s*(moi|khac)"}
    for u in UNITS:
        for m in re.finditer(r"\b" + u + r"\b", text):
            if any(a <= m.start() < b for a, b in spans):
                continue
            pat = bad_next.get(u)
            if pat and re.match(pat, text[m.end():]):
                continue
            return u
    return None


def parse_threshold(qraw):
    """Parse a money threshold like '9.800.000 đồng trở lên'."""
    q = qraw
    for m in re.finditer(r"(\d[\d.,]*)\s*(tr|k|đồng|dong|đ|d)\b", q, re.IGNORECASE):
        raw = m.group(1)
        unit = m.group(2).lower()
        # skip dates
        if re.search(r"\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4}", q[max(0, m.start() - 3): m.end() + 3]):
            continue
        try:
            if unit == "tr":
                val = float(raw.replace(",", ".")) * 1_000_000
            elif unit in ("đồng", "dong"):
                val = float(raw.replace(".", "").replace(",", ""))
            elif unit == "k":
                val = float(raw.replace(",", ".")) * 1_000
            else:
                s = raw.replace(".", "").replace(",", "")
                val = float(s)
        except ValueError:
            continue
        if val >= 1000:
            return val
    return None


WALKIN = {"khach le", "khach le", "le", "kl", "nan", "none", "", "khach vang lai", "vang lai", "khach hang le"}


def _unique_norm(series):
    out = []
    for v in pd.unique(series.astype(str)):
        s = str(v).strip()
        if not s or s.lower() in ("nan", "none"):
            continue
        out.append(s)
    return out


def find_shift(qn):
    if re.search(r"\bca sang\b|buoi sang|\bca 1\b|morning", qn):
        return "sang"
    if re.search(r"\bca chieu\b|buoi chieu|\bca 2\b|afternoon", qn):
        return "chieu"
    return None


PAY_ALIASES = [
    (r"tien mat|\btm\b|tra bang tm", ["tien mat", "cash", "tm"]),
    (r"chuyen khoan|\bck\b|ngan hang|bank", ["chuyen khoan", "transfer", "ck", "bank"]),
    (r"\bcod\b|thu ho|giao hang thu tien", ["cod", "thu ho"]),
    (r"vi dien tu|\bvi\b|ewallet|momo|zalopay|vnpay", ["vi dien tu", "ewallet", "vi", "momo"]),
    (r"\bthe\b|credit|debit|card", ["the", "card", "credit"]),
    (r"ghi no|\bdebt\b", ["ghi no", "debt"]),
]


def find_payment_value(qn, values):
    vals = _unique_norm(values)
    for pat, aliases in PAY_ALIASES:
        if re.search(pat, qn):
            for v in vals:
                nv = norm_name(v)
                if any(a in nv for a in aliases):
                    return v
    return None


def find_payments_all(qn, values):
    found = []
    vals = _unique_norm(values)
    for pat, aliases in PAY_ALIASES:
        m = re.search(pat, qn)
        if m:
            for v in vals:
                nv = norm_name(v)
                if any(a in nv for a in aliases):
                    found.append((m.start(), v))
                    break
    found.sort(key=lambda t: t[0])
    return [v for _, v in found]


def cand_payment_list(span, vals):
    code = _head("lines", span, True, "_l")
    norm_vals = [norm_name(v) for v in vals]
    code += f"_vals = {norm_vals!r}\n"
    code += "RESULT = [int(round(float(_l[_l['_payment'].map(normalize_text) == v]['_revenue'].sum()))) for v in _vals]\n"
    return code


def find_staff(qn, frames):
    o = frames["orders"]
    if "_staff" not in o.columns:
        return None
    # code form: nv001 / nv 1
    m = re.search(r"\bnv\s*0*(\d+)\b", qn)
    if m:
        want = "nv%03d" % int(m.group(1))
        for v in _unique_norm(o["_staff"]):
            if norm_name(v) == want:
                return ("code", v)
    # name form
    if "_staff_name" in o.columns:
        pairs = [(norm_name(v), v) for v in _unique_norm(o["_staff_name"])]
        pairs = [p for p in pairs if len(p[0]) >= 4]
        hit = find_in_text(qn, pairs)
        if hit:
            return ("name", hit[1])
    return None


TIER_ALIASES = [
    (r"than thiet|than thiet|vip", ["than thiet", "vip"]),
    (r"\ble\b|khach le|vang lai|walk in", ["le", "vang lai"]),
    (r"\bsi\b|khach si|ban si|dai ly", ["si", "dai ly"]),
]


def find_tier(qn, customers):
    if "_tier" not in customers.columns:
        return None
    vals = _unique_norm(customers["_tier"])
    for pat, aliases in TIER_ALIASES:
        if re.search(pat, qn):
            for v in vals:
                nv = norm_name(v)
                if any(nv == a or a in nv for a in aliases):
                    return v
    return None


def find_size(qn):
    m = re.search(r"\bsize\s*([ml])\b|\bco\s+([ml])\b|\bsize\s+([ml])\b", qn)
    if m:
        return (m.group(1) or m.group(2) or m.group(3)).lower()
    return None


def find_ingredient(qn, lines):
    if "_ingredient" not in lines.columns:
        return None
    m = re.search(r"hoat chat\s+([a-z0-9 ]+)$", qn)
    tail = qn
    if m:
        tail = m.group(1)
    # longest known ingredient contained in the question
    vals = [(norm_name(v), v) for v in _unique_norm(lines["_ingredient"])]
    vals = [v for v in vals if len(v[0]) >= 4]
    hit = find_in_text(qn, vals)
    if hit:
        return hit[0]
    return None


# ---------------------------------------------------------------------------
# candidate generation
# ---------------------------------------------------------------------------
def gen_candidates(qraw, asof, spec, frames, prods, cats):
    qn = norm_q(qraw)
    a = pd.Timestamp(asof)
    spans = parse_spans(qraw, asof)
    primary = spans[0] if spans else None

    cands: list[dict] = []

    def add(score, intent, code):
        cands.append(dict(score=score, intent=intent, code=code))

    prod = find_in_text(qraw, prods)
    cat = find_in_text(qraw, cats)
    unit = find_unit_outside(qn, norm_name(prod[1]) if prod else None, qraw)
    threshold = parse_threshold(qraw)

    has_orders = "orders" in frames and len(frames["orders"]) > 0
    has_lines = "lines" in frames and len(frames["lines"]) > 0
    has_stock = "stock" in frames and len(frames["stock"]) > 0
    has_customers = "customers" in frames and len(frames["customers"]) > 0
    has_purch = "purchases" in frames and len(frames["purchases"]) > 0
    has_price = "price_history" in frames and len(frames["price_history"]) > 0
    has_customer_data = bool(has_orders and frames["orders"]["_customer"].astype(str).str.strip().ne("").any())

    shift_val = find_shift(qn)
    pay_val = find_payment_value(qn, frames["orders"]["_payment"]) if has_orders else None
    staff_hit = find_staff(qn, frames) if has_orders else None
    tier_val = find_tier(qn, frames["customers"]) if "customers" in frames else None
    size_val = find_size(qn)
    ingr_val = find_ingredient(qn, frames["lines"]) if has_lines else None

    def prod_norm(x):
        return norm_name(x[1]) if x else None

    # ---------- boolean trend ----------
    if re.search(r"tang (lien tuc|deu|dan)|co tang|tang khong|giam lien tuc", qn):
        months = []
        for s in spans:
            if s["kind"] == "month":
                t = pd.Timestamp(s["start"])
                months.append((t.year, t.month))
        # try to find 3 consecutive months
        if len(months) < 3:
            ms = sorted(set(months))
            if len(ms) >= 2:
                months = ms
        if len(months) >= 2:
            add(90, "trend", cand_trend(months))
            add(88, "trend_lines", cand_trend(months, use_lines=True))

    # ---------- price-change quantity effect ----------
    mp = re.search(r"(\d+)\s*ngay\s*ke tu\s*(?:ngay\s*)?(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", qn)
    ref_ts = None
    n = 7
    if mp:
        n = int(mp.group(1))
        try:
            ref_ts = pd.Timestamp(int(mp.group(4)), int(mp.group(3)), int(mp.group(2)))
        except ValueError:
            ref_ts = None
    else:
        mref = re.search(r"(\d+)\s*ngay\s*ke tu\s*(?:ngay\s*)?(?:do|ngay do|ngay tang gia|ngay doi gia|ngay tang|ngay doi)", qn)
        if mref:
            n = int(mref.group(1))
            for _s in spans:
                if _s["kind"] == "day":
                    ref_ts = pd.Timestamp(_s["start"])
                    break
    # price change with no explicit date -> look it up in the price history
    if ref_ts is None and prod:
        _ph = frames.get("price_history")
        if _ph is not None and len(_ph):
            _mnew = re.search(r"tang gia len\s*([\d][\d.,]*)", qn)
            _target = None
            if _mnew:
                try:
                    _target = float(_mnew.group(1).replace(".", "").replace(",", ""))
                except ValueError:
                    _target = None
            if _target:
                _pn = prod_norm(prod)
                _pc = _ph["_pname"] if "_pname" in _ph.columns else _ph["_product"]
                _cand = _ph[_pc.map(norm_name).str.contains(_pn, na=False, regex=False)]
                _cand = _cand[_cand["_old_price"].notna()]
                if len(_cand):
                    _cand = _cand.assign(_diff=(_cand["_new_price"] - _target).abs()).sort_values("_diff")
                    _row = _cand.iloc[0]
                    if abs(float(_row["_new_price"]) - _target) <= max(1.0, _target * 0.02):
                        ref_ts = pd.Timestamp(_row["_date"])

    if ref_ts is not None and prod and re.search(r"truoc do|ngay truoc|ngay trc|lien truoc|truoc ngay|ngay ngay truoc", qn):
        s0 = ref_ts
        if s0 is not None:
            b0 = s0 - pd.Timedelta(days=n)
            b1 = s0 - pd.Timedelta(days=1)
            a1 = s0 + pd.Timedelta(days=n - 1)
            add(99, "price_effect_qty", cand_pct_change_periods(
                b0.date().isoformat(), b1.date().isoformat(),
                s0.date().isoformat(), a1.date().isoformat(),
                product=prod_norm(prod), by="qty"))
            add(97, "price_effect_qty_base", cand_pct_change_periods(
                b0.date().isoformat(), b1.date().isoformat(),
                s0.date().isoformat(), a1.date().isoformat(),
                product=prod_norm(prod), by="qty_base"))
            add(95, "price_effect_rev", cand_pct_change_periods(
                b0.date().isoformat(), b1.date().isoformat(),
                s0.date().isoformat(), a1.date().isoformat(),
                product=prod_norm(prod), by="revenue"))

    # Tet season vs the same number of days immediately before it
    if re.search(r"\btet\b", qn) and re.search(r"truoc tet|truoc ngay tet", qn) and re.search(
        r"hon hay kem|tang hay giam|thay doi|bao nhieu %|may %|%", qn
    ):
        _tsp = next((x for x in spans if str(x.get("label", "")).startswith("tet ")), None)
        if _tsp and _tsp.get("start") is not None and _tsp.get("end") is not None:
            _s0 = pd.Timestamp(_tsp["start"]); _e0 = pd.Timestamp(_tsp["end"])
            _days = (_e0 - _s0).days + 1
            _b0 = _s0 - pd.Timedelta(days=_days); _b1 = _s0 - pd.Timedelta(days=1)
            add(99, "pct_tet", cand_pct_change_periods(
                _b0.date().isoformat(), _b1.date().isoformat(),
                _s0.date().isoformat(), _e0.date().isoformat(), use_lines=False))
            add(97, "pct_tet_lines", cand_pct_change_periods(
                _b0.date().isoformat(), _b1.date().isoformat(),
                _s0.date().isoformat(), _e0.date().isoformat(), use_lines=True))

    # ---------- same period last year / month ----------
    if re.search(r"cung ky nam truoc|cung ky nam ngoai|so voi cung ky nam", qn):
        months = mentioned_months(qraw, asof)
        if months:
            y, m = months[0]
            add(98, "pct_yoy", cand_pct_change(y - 1, m, y, m))
            add(96, "pct_yoy_lines", cand_pct_change(y - 1, m, y, m, use_lines=True))
    if re.search(r"cungf? ky th(?:ang)?\s*(truoc|roi|trc)", qn) and re.search(r"dau thang", qn):
        add(99, "pct_mtd", cand_pct_change_mtd(asof))
        add(97, "pct_mtd_lines", cand_pct_change_mtd(asof, use_lines=True))

    # ---------- percent change ----------
    if re.search(r"tang hay giam|thay doi bao nhieu|tang truong bao nhieu|hon hay kem|so voi thang|so voi cung ky|tang hay giam may|tang giam bao nhieu|thay doi may|tang hay giam bnhiu|giam bnhiu", qn):
        months = mentioned_months(qraw, asof)
        cur = None
        prev = None
        mcmp = re.search(r"so voi thang\s+(\d{1,2})\s*[/\-.]\s*(\d{4})", qn)
        if mcmp:
            prev = (int(mcmp.group(2)), int(mcmp.group(1)))
            for mo in months:
                if mo != prev:
                    cur = mo
                    break
        if cur is None:
            if len(months) >= 2:
                prev, cur = months[0], months[1]
            elif len(months) == 1:
                cur = months[0]
                prev = _shift_month(cur[0], cur[1], -1)
            else:
                for s in spans:
                    if s["kind"] == "month":
                        t = pd.Timestamp(s["start"])
                        cur = (t.year, t.month)
                        break
                if cur is None and re.search(r"thang nay", qn):
                    cur = (a.year, a.month)
                if cur:
                    prev = _shift_month(cur[0], cur[1], -1)
        if cur and prev:
            add(95, "pct_change", cand_pct_change(prev[0], prev[1], cur[0], cur[1]))
            add(92, "pct_change_lines", cand_pct_change(prev[0], prev[1], cur[0], cur[1], use_lines=True))
            add(94, "pct_change_na", cand_pct_change_na(prev[0], prev[1], cur[0], cur[1]))

    # ---------- best day ----------
    if re.search(r"ngay\s*na[o0]?f?\b.*(nhieu|nhiu|nhiee|nhieuf|cao|dat|lon).*nha+t?s?|ngay\s*na[o0]?f?\b.*ban (dc|duoc)|xet theo (dthu|doanh thu) ngay", qn):
        add(96, "best_day", cand_best_day(primary))
        add(94, "best_day_lines", cand_best_day(primary, use_lines=True))
        add(90, "max_day_rev", cand_max_day_rev(primary))

    # ---------- best month (date answer) ----------
    if re.search(r"thang nao|thang may|thang nao.*(nhieu|cao|dat|lon)", qn) and re.search(
        r"nhieu tien nhat|cao nhat|ban (dc|duoc) nhieu|doanh thu (cao|lon|nhieu)|dat nhat|lon nhat|it nhat", qn
    ):
        months = mentioned_months(qraw, asof)
        if not months and primary and primary["kind"] in ("range", "year"):
            s0 = pd.Timestamp(primary["start"] or a)
            e0 = pd.Timestamp(primary["end"] or a)
            cur = pd.Timestamp(s0.year, s0.month, 1)
            while cur <= e0:
                months.append((cur.year, cur.month))
                cur = cur + pd.DateOffset(months=1)
        if len(months) >= 2:
            mode = "min" if re.search(r"it nhat|thap nhat", qn) else "max"
            add(97, "best_month", cand_best_month(months, mode=mode))
            add(95, "best_month_lines", cand_best_month(months, use_lines=True, mode=mode))

    # ---------- days above threshold ----------
    if threshold and re.search(r"so ngay|may ngay|bao nhieu ngay", qn):
        add(97, "days_above", cand_days_above(primary, threshold))
        add(95, "days_above_lines", cand_days_above(primary, threshold, use_lines=True))

    # ---------- products in >= N orders ----------
    m = re.search(r"(?:tu|>=|≥|its? nhat|toi thieu)\s*(\d+)\s*don", qn)
    if m and re.search(r"san pham|mat hang|hang hoa", qn):
        add(97, "products_min_orders", cand_products_min_orders(primary, int(m.group(1))))

    # ---------- customers ----------
    if re.search(r"khach|ai mua|nguoi mua|mua hang nhieu|mua nhieu tien", qn):
        if not has_customer_data:
            add(99, "unanswerable", "RESULT = 'unanswerable'\n")
        else:
            m2 = re.search(r"(?:tu|>=|≥|its? nhat|toi thieu)\s*(\d+)\s*don", qn)
            if m2 and re.search(r"chiem|ti le|%|bao nhieu %|may %|phan tram", qn):
                add(97, "customers_min_orders_pct",
                    cand_customers_min_orders(primary, int(m2.group(1)), percent=True))
            elif m2:
                add(96, "customers_min_orders",
                    cand_customers_min_orders(primary, int(m2.group(1))))
            if re.search(r"chua tra|con no|cong no|no cua hang", qn):
                add(96, "debt_customers", cand_debt_customers(primary))
                add(94, "debt_sum", cand_debt_sum(primary))
            if re.search(r"no nhieu nhat|chi tieu nhieu|mua nhieu|mua nhieu tien|mua nhiu|chi tieu nhiu|cao nhat|nhieu tien nhat|top|liet ke", qn):
                n = 5
                m3 = re.search(r"top\s*(\d+)", qn)
                if m3:
                    n = int(m3.group(1))
                else:
                    m3b = re.search(r"(\d+)\s*khach", qn)
                    if m3b:
                        n = int(m3b.group(1))
                add(95, "top_customers", cand_top_customers(primary, n))
                add(93, "top_customers_tie", cand_top_customers(primary, n, tie_name=True))
            if re.search(r"mua nhieu don|nhieu don nhat|so don nhieu nhat|mua nhieu ddown", qn):
                add(97, "best_customer_orders", cand_best_customer_orders(primary))
            if re.search(r"chi tieu nhieu|mua nhieu tien|mua nhiu|mua hang nhieu tien|ai mua.*nhieu|khach nao.*nhieu nhat|mua nhieu nhat", qn) and not re.search(r"mua nhieu don|nhieu don nhat", qn):
                add(96, "best_customer", cand_top_customer_one(primary))
                add(94, "best_customer_list", cand_top_customers(primary, 1))

    # ---------- debt ----------
    top_n = 5
    _mn = re.search(r"\b(\d{1,2})\b\s*(?:khach|nguoi|ban ghi|dong)", qn)
    if _mn and 1 <= int(_mn.group(1)) <= 20:
        top_n = int(_mn.group(1))
    else:
        _mn2 = re.search(r"top\s*(\d{1,2})", qn)
        if _mn2 and 1 <= int(_mn2.group(1)) <= 20:
            top_n = int(_mn2.group(1))
    cust_hit = find_customer(qn, frames)
    if re.search(r"\btra\w*\b.{0,12}\bno\b|thu duoc.*tra no|khach tra no|tra not|thu hoi|thu no", qn):
        add(99, "debt_paid", cand_debt_paid(primary))
    if cust_hit and re.search(r"ghi no|no them|tra no", qn):
        add(99, "debt_pair", cand_debt_pair(primary, cust_hit[0]))
    _debt_q = bool(re.search(r"\bno\b|cong no|tra no|tra bot no|khach tra no|tien no|con no|chua tra", qn))
    if _debt_q and not _debt_available(frames):
        add(100, "unanswerable_debt", "RESULT = 'unanswerable'\n")
    if _debt_q:
        if re.search(r"nhieu nhat|top|liet ke", qn):
            add(97, "debt_at_top", cand_debt_at_top(primary, asof, top_n))
            add(95, "debt_top", cand_debt_top(primary, 5))
        else:
            if re.search(r"khach|nguoi|so khach|bao nhieu khach|may khach", qn):
                add(97, "debt_at_customers", cand_debt_at_customers(primary, asof))
                add(95, "debt_customers_static", cand_debt_static_customers(primary))
            if re.search(r"tuoi no|nhom tuoi|0.?7|8.?15|tren 15", qn):
                add(98, "debt_age_buckets", cand_debt_age_buckets(primary, asof))
            m_age = re.search(r"(?:qua|hon|tren)\s*(\d+)\s*ngay", qn)
            if m_age:
                add(98, "debt_at_sum_age", cand_debt_at_sum(primary, asof, int(m_age.group(1))))
            add(97, "debt_at_sum", cand_debt_at_sum(primary, asof))
            add(94, "debt_sum", cand_debt_sum(primary))
            add(92, "debt_sum_plain", cand_debt_sum(primary, exclude_cod_cancel=False))

    # ---------- stock ----------
    if re.search(r"ton kho|ton cuoi|ton thuc|con bao nhieu|con ton|ton bao nhieu", qn):
        if has_stock:
            add(96, "stock_sum", cand_stock_sum(prod_norm(prod)))
        else:
            add(96, "unanswerable", "RESULT = 'unanswerable'\n")

    # ---------- purchases ----------
    if re.search(r"nhap hang|phieu nhap|tien nhap|nhap vao|gia nhap|nhap bao nhieu|tong gia tri.*nhap|nhap trong|\bnhap\b", qn):
        if has_purch:
            add(95, "purchase_sum", cand_purchase_sum(primary))
            if prod:
                add(99, "purchase_avg", cand_purchase_avg(primary, prod_norm(prod), unit))
                add(97, "purchase_avg_all", cand_purchase_avg(primary, prod_norm(prod), None))
            if re.search(r"cung cap|ncc|nha cc|nha cung", qn):
                add(99, "supplier_top", cand_supplier_top(primary))
        else:
            add(94, "unanswerable", "RESULT = 'unanswerable'\n")

    # ---------- price ----------
    if re.search(r"gia ban|gia bao nhieu|gia cua|gia moi|gia cu|doi gia|gia niem yet|gia 1|don gia", qn) and not re.search(r"nhap", qn):
        if prod:
            # date in question
            dt = None
            for s in spans:
                if s["kind"] == "day":
                    dt = s["start"]
                    break
            if dt and has_price:
                add(97, "price_at", cand_price_at(prod_norm(prod), dt))
            # price from lines on the span
            uf = ""
            if unit:
                uf = f"_u = _l[_l['_unit'].map(normalize_text) == {norm_name(unit)!r}]\nif len(_u):\n    _l = _u\n"
            code = _head("lines", primary, True, "_l")
            code += f"_l = _l[_l['_product'].map(normalize_text) == {prod_norm(prod)!r}]\n"
            code += uf
            code += "RESULT = int(round(float(_l['_revenue'].sum() / _l['_qty'].sum()))) if _l['_qty'].sum() else 'unanswerable'\n"
            add(90, "avg_price", code)
            code_b = _head("lines", primary, True, "_l")
            code_b += f"_l = _l[_l['_product'].map(normalize_text) == {prod_norm(prod)!r}]\n"
            code_b += uf
            code_b += "RESULT = int(round(float(_l['_revenue'].sum() / _l['_qty_base'].sum()))) if _l['_qty_base'].sum() else 'unanswerable'\n"
            add(93, "avg_price_base", code_b)

    # ---------- top products ----------
    if re.search(r"top\s*\d+|liet ke|ban chay nhat|ban chay|ban nhieu nhat|chay nhat|hot nhat|ban (dc|duoc) nhieu nhat|nhieu nhat.*(san pham|mat hang|hang)|(san pham|mat hang|hang|sp).*(nhieu nhat|ban chay|chay nhat|hot nhat)|\b(mat hang|san pham|sp|hang|mon|thuoc)\s+na[o0]?f?\b", qn):
        n = 5
        m4 = re.search(r"top\s*(\d+)", qn)
        if m4:
            n = int(m4.group(1))
        else:
            m5 = re.search(r"(?<![\d/])(\d+)\s*(?:mat hang|san pham|sp|hang hoa|mon|loai|khach)", qn)
            if m5:
                n = int(m5.group(1))
        single = not re.search(r"top\s*\d+|(?<![\d/])\d+\s*(mat hang|san pham|sp|hang hoa|hang|mon|loai)|liet ke|nhung|cac |moi loai", qn)
        if single:
            add(96, "top_product_one", cand_top_product_one(primary, "qty_base"))
            add(95, "top_product_one_qty", cand_top_product_one(primary, "qty"))
            add(94, "top_product_one_rev", cand_top_product_one(primary, "revenue"))
            add(92, "top_product_one_cnt", cand_top_product_one(primary, "count"))
            add(93, "top_product_one_tie", cand_top_products_tie(primary, 1, "qty_base"))
            add(91, "top_product_one_cnt_tie", cand_top_products_tie(primary, 1, "count"))
        else:
            add(96, "top_products_qty", cand_top_products(primary, n, "qty_base"))
            add(94, "top_products_qty2", cand_top_products(primary, n, "qty"))
            add(92, "top_products_rev", cand_top_products(primary, n, "revenue"))
            add(90, "top_products_cnt", cand_top_products(primary, n, "count"))
            add(95, "top_products_qty_tie", cand_top_products_tie(primary, n, "qty_base"))
            add(93, "top_products_qty2_tie", cand_top_products_tie(primary, n, "qty"))
            add(91, "top_products_rev_tie", cand_top_products_tie(primary, n, "revenue"))
            add(89, "top_products_cnt_tie", cand_top_products_tie(primary, n, "count"))

    # ---------- share / percentage ----------
    if re.search(r"ti trong|chiem|bang bao nhieu %|may %|bao nhieu phan tram|ti le.*(doanh thu|dthu)|dong gop|bnhiu %|bao nhieu %|phan tram.*(doanh thu|dthu)|% doanh thu", qn):
        if prod or cat:
            add(96, "share_rev", cand_share(primary, cat_match=cat[0] if cat else None,
                                            product_match=prod_norm(prod) if prod else None))
            add(94, "share_qty", cand_share(primary, cat_match=cat[0] if cat else None,
                                            product_match=prod_norm(prod) if prod else None, by="qty"))
        if re.search(r"huy", qn):
            add(95, "cancel_rate", cand_cancel_rate(primary))
            add(93, "cancel_rate_total", cand_cancel_rate(primary, denom="total"))

    # ---------- cancel ----------
    if re.search(r"huy|huy don|don bi huy|don da huy|trang thai huy", qn):
        if re.search(r"ti le|%|phan tram|may %|bao nhieu %", qn):
            add(99, "cancel_rate", cand_cancel_rate(primary, denom="total", mask="cancelled"))
            add(97, "cancel_rate_nonreturned", cand_cancel_rate(primary, denom="nonreturned", mask="cancelled"))
            add(95, "cancel_rate_bad", cand_cancel_rate(primary, denom="total", mask="bad"))
        else:
            add(99, "cancel_count", cand_cancel_count(primary, mask="cancelled"))
            add(97, "cancel_count_bad", cand_cancel_count(primary, mask="bad"))

    # ---------- product-specific quantity / revenue ----------
    if prod and re.search(r"nhieu tie|bao nhieu tie|doanh thu|thu ve|thu duoc|tong cong.*tie|tie+n|tie+f", qn):
        code0 = _head("lines", primary, True, "_l")
        code0 += f"_l = _l[_l['_product'].map(normalize_text) == {prod_norm(prod)!r}]\n"
        code0 += "RESULT = int(round(float(_l['_revenue'].sum())))\n"
        add(97, "product_rev", code0)
    if prod and re.search(r"ban (duoc|dc|ra)|thu ve|doanh thu|bao nhieu|tong cong|tieu thu", qn):
        code = _head("lines", primary, True, "_l")
        code += f"_l = _l[_l['_product'].map(normalize_text) == {prod_norm(prod)!r}]\n"
        if unit:
            code += f"_l = _l[_l['_unit'].map(normalize_text) == {norm_name(unit)!r}]\n"
        code += "RESULT = int(round(float(_l['_qty'].sum())))\n"
        add(95, "product_qty", code)
        code2 = _head("lines", primary, True, "_l")
        code2 += f"_l = _l[_l['_product'].map(normalize_text) == {prod_norm(prod)!r}]\n"
        code2 += "RESULT = int(round(float(_l['_qty_base'].sum())))\n"
        add(93, "product_qty_base", code2)
        code3 = _head("lines", primary, True, "_l")
        code3 += f"_l = _l[_l['_product'].map(normalize_text) == {prod_norm(prod)!r}]\n"
        code3 += "RESULT = int(round(float(_l['_revenue'].sum())))\n"
        add(92, "product_rev", code3)

    # ---------- orders above revenue threshold ----------
    if threshold and re.search(r"so don|may don|bao nhieu don|bn don|bill|hoa don|don co|don hang", qn) and (
        re.search(r"tro len|>=|toi thieu|its? nhat", qn) or "≥" in qraw or ">=" in qraw
    ):
        add(98, "orders_above", cand_orders_above(primary, threshold, bad=True))
        add(96, "orders_above_all", cand_orders_above(primary, threshold, bad=False))
        add(95, "orders_above_lines", cand_orders_above_lines(primary, threshold))

    # ---------- dimension-filtered revenue / qty / count ----------
    dims = []
    if cat:
        dims.append(("_category", norm_name(cat[1]), "lines", False, None))
    if size_val:
        dims.append(("_size", size_val, "lines", False, None))
    if shift_val:
        dims.append(("_shift", shift_val, "lines", False, None))
    if pay_val:
        dims.append(("_payment", norm_name(pay_val), "lines", False, None))
    if tier_val:
        dims.append(("_tier", norm_name(tier_val), "lines", False, None))
    if staff_hit:
        kind, val = staff_hit
        if kind == "code":
            dims.append(("_staff", val, "lines", False, None))
        else:
            dims.append(("_staff", "", "lines", False, val))
    for dim_col, dim_val, tbl, contains, sname in dims:
        ul = tbl == "lines"
        add(93, f"rev_dim{dim_col}", cand_metric_dim(primary, dim_col, dim_val, "revenue",
                                                    use_lines=ul, contains=contains, staff_name=sname))
        if ul:
            add(90, f"qty_dim{dim_col}", cand_metric_dim(primary, dim_col, dim_val, "qty_base",
                                                        use_lines=ul, contains=contains, staff_name=sname))
        if dim_col in ("_shift", "_payment", "_tier", "_staff"):
            add(88, f"cnt_dim{dim_col}", cand_metric_dim(primary, dim_col, dim_val, "orders",
                                                        use_lines=False, contains=contains, staff_name=sname))
    if ingr_val:
        add(98, "rev_ingr", cand_revenue_ingr(primary, ingr_val))
        add(96, "rev_ingr_contains", cand_revenue_ingr(primary, ingr_val, contains_only=True))
        add(94, "qty_ingr", cand_revenue_ingr(primary, ingr_val, metric="qty_base"))
        add(92, "qty_ingr2", cand_revenue_ingr(primary, ingr_val, metric="qty"))
    if has_orders and re.search(r"moi loai|tung loai|mỗi loại|từng loại", qn):
        pvals = find_payments_all(qn, frames["orders"]["_payment"])
        if len(pvals) >= 2:
            add(98, "payment_list", cand_payment_list(primary, pvals))
    if re.search(r"bang bao nhieu %|may %|ti trong|chiem|phan tram", qn):
        if pay_val:
            add(95, "share_payment", cand_metric_dim(primary, "_payment", norm_name(pay_val),
                                                     "share", use_lines=True))
        if tier_val:
            add(95, "share_tier", cand_metric_dim(primary, "_tier", norm_name(tier_val),
                                                  "share", use_lines=True))
        if cat:
            add(94, "share_cat", cand_metric_dim(primary, "_category", norm_name(cat[1]),
                                                 "share", use_lines=True))

    # ---------- best staff ----------
    if re.search(r"nhan vien", qn) and re.search(r"gioi nhat|xuat sac|ban chay nhat|nhieu nhat|top", qn):
        add(97, "best_staff", cand_best_staff(primary))
        add(95, "best_staff_name", cand_best_staff(primary, use_name=True))

    # ---------- multi-month revenue lists ----------
    mm = mentioned_months(qraw, asof)
    mc = re.search(r"(\d+)\s*thang\s*lien", qn)
    if mc and mm:
        n = int(mc.group(1))
        y, m = mm[-1]
        months = []
        for k in range(n - 1, -1, -1):
            months.append(_shift_month(y, m, -k))
        add(99, "month_list_consec", cand_month_list(months))
        add(97, "month_list_consec_lines", cand_month_list(months, use_lines=True))
    elif len(mm) >= 2 and re.search(r"moi thang|lan luot|thu tu|theo thu tu|ghi .*thu tu|thang .* va thang", qn):
        add(99, "month_list_explicit", cand_month_list(mm))
        add(97, "month_list_explicit_lines", cand_month_list(mm, use_lines=True))

    # ---------- deliveries ----------
    has_deliv = "deliveries" in frames and len(frames["deliveries"]) > 0
    if re.search(r"dot (giao|hang)|giao hang|chuyen giao|cho giao|xe (da )?giao|phieu giao", qn) and re.search(
        r"may|bao nhieu|bnhiu|bn|dem|so dot|tong cong|total", qn
    ):
        if has_deliv:
            add(99, "delivery_count", cand_delivery_count(primary))
        else:
            add(90, "unanswerable", "RESULT = 'unanswerable'\n")

    # ---------- stock parts (large + remainder) ----------
    has_lots = "lots" in frames and len(frames["lots"]) > 0
    if prod and re.search(r"chan|\ble\b|may (hop|goi|chai|vi|thung|cai|ong|cuon)", qn) and re.search(
        r"ton kho|con may|con (may|bao nhieu)|con lai", qn
    ):
        if has_stock or has_lots:
            add(99, "stock_parts", cand_stock_parts(prod_norm(prod), conv_ratio(frames, prod_norm(prod)), asof))

    # ---------- lot expiry ----------
    if prod and has_lots and re.search(r"han (dung|su dung)|het han|gan het han", qn):
        add(99, "lot_expiry", cand_lot_expiry(prod_norm(prod), asof))
    mexp = re.search(r"han (?:dung|su dung) tu (\d{1,2})/(\d{1,2})/(\d{4}) den (?:het )?(\d{1,2})/(\d{1,2})/(\d{4})", qn)
    if mexp and has_lots:
        d0 = f"{mexp.group(3)}-{int(mexp.group(2)):02d}-{int(mexp.group(1)):02d}"
        d1 = f"{mexp.group(6)}-{int(mexp.group(5)):02d}-{int(mexp.group(4)):02d}"
        add(99, "lot_expiring_value", cand_lot_expiring_value(d0, d1, asof))

    # ---------- shift comparison ----------
    if re.search(r"ca (sang|chieu)|ca sang|ca chieu", qn) and re.search(
        r"hon hay kem|tang hay giam|bao nhieu %|phan tram|may %|nhieu hon|it hon", qn
    ):
        add(99, "shift_pct", cand_shift_pct(primary))

    # ---------- channel ----------
    chans = find_channels_all(qn)
    if chans and has_orders:
        if len(chans) >= 2:
            add(98, "channel_list", cand_channel_list(primary, chans))
        for _ch in chans:
            add(97, f"channel_rev_{_ch}", cand_channel_rev(primary, _ch))
        if re.search(r"chiem|ti trong|phan tram|%|dong gop|bang bao nhieu|bnhiu", qn):
            for _ch in chans:
                add(98, f"channel_share_{_ch}", cand_channel_share(primary, _ch))
                add(97, f"channel_share_order_{_ch}", cand_share_channel(primary, _ch))

    # ---------- prescription ----------
    if re.search(r"ke don|thuoc ke|khong ke don|hong ke don|ko ke don|tru thuoc ke don|thuoc ke don", qn):
        add(99, "rx_rev_true", cand_rx_metric(primary, "rev_true"))
        if re.search(r"tru|loai ra|con lai|khong ke don|hong ke don|ko ke don|khong phai", qn):
            add(99, "rx_rev_false", cand_rx_metric(primary, "rev_false"))
        if re.search(r"chiem|phan tram|%|ti trong", qn):
            add(99, "rx_share", cand_rx_metric(primary, "share_true"))

    # ---------- gross profit ----------
    if re.search(r"loi (gop|nhuan)|lai gop|gross|loi nhuan|loi nhuan gop", qn):
        add(99, "gross_profit", cand_gross_profit(primary))

    # ---------- stock value at cost ----------
    if re.search(r"trong kho|nam trong kho|ton kho|gia tri kho", qn) and re.search(
        r"gia von|tien hang|gia tri|theo gia", qn
    ) and has_stock:
        add(99, "stock_value", cand_stock_value())
        add(96, "stock_value_no_bad", cand_stock_value())

    # ---------- zero sales ----------
    if re.search(r"bi e\b|hang e\b|mat hang e\b|e han|khong ai mua|khong ban (dc|duoc)|ban ko dc|ban khong dc|khong ban duoc|ban ko duoc", qn):
        add(99, "zero_sales", cand_zero_sales(primary))

    # ---------- generic revenue / count / avg ----------
    if has_orders:
        # explicit "so don" / "may don" / "bao nhieu don"
        if re.search(r"\b(d+o+w?n|ddo+n|bill|hoa don|chung tu|don hang|don dat)\b", qn) and not re.search(r"don gia|don vi", qn) and re.search(r"\b(so+s?|soo|may|bao nhieu|bnhiu|bn|nhieu|nhiu|tong cong|dem|co|hom nay|ho+m nay|hnay|hqua|hom qua|qua)\b", qn):
            add(90, "order_count", cand_order_count(primary))
            add(88, "order_count_all", cand_order_count(primary, bad=False))
            add(86, "line_count", cand_line_count(primary))
        if re.search(r"trung binh|binh quan|moi don|tren mot don|tren 1 don|mot don", qn):
            add(90, "avg_order", cand_avg_order(primary))
            add(88, "avg_order_lines", cand_avg_order(primary, use_lines=True))
        if re.search(r"doanh thu|dthu|\bdt\b|revenue|thu duoc|ban duoc|ban dc|thu ve|doanh so|tong cong bao nhieu tien|bao nhieu tien|tien", qn):
            add(85, "revenue", cand_revenue(primary))
            add(83, "revenue_lines", cand_revenue(primary, use_lines=True))
            add(80, "revenue_all", cand_revenue(primary, bad=False))

    # ---------- generic qty ----------
    if has_lines and (unit or re.search(r"so luong|ban duoc|ban dc|tieu thu|kg|lon|chai|hop|goi|thung|ly|cai|phan|dia|suat", qn)):
        add(80, "qty_base", cand_qty(primary, base=True))
        add(78, "qty_raw", cand_qty(primary, base=False))
        if unit and not prod and not cat and not size_val:
            add(97, "qty_unit", cand_qty_unit(primary, unit))

    # ---------- unanswerable fallback for missing data ----------
    if re.search(r"ton kho|ton cuoi", qn) and not has_stock:
        add(99, "unanswerable", "RESULT = 'unanswerable'\n")
    if re.search(r"khach hang|khach nao|thong tin khach", qn) and not has_customers and not has_orders:
        add(99, "unanswerable", "RESULT = 'unanswerable'\n")

    # questions that reference fields absent from the canonical model
    if re.search(r"\bduong\b|dia chi|nha o|cho o\b|o dau", qn) and re.search(r"khach|nha", qn):
        add(100, "unanswerable_addr", "RESULT = 'unanswerable'\n")
    if re.search(r"gioi tinh|khach nu|khach nam|nam hay nu", qn):
        add(100, "unanswerable_gender", "RESULT = 'unanswerable'\n")
    if re.search(r"lanh nghe|tan tam|le phep|hay khen|khen nhieu|quy men|thai do|hai long", qn):
        add(100, "unanswerable_staff", "RESULT = 'unanswerable'\n")
    if re.search(r"tra hang vi|mua nham|loi va|huy vi|vi sao.*(huy|tra)|ly do.*(huy|tra)|nguyen nhan.*(huy|tra)", qn):
        add(100, "unanswerable_reason", "RESULT = 'unanswerable'\n")

    # span entirely before the available data
    if primary is not None:
        _mins = []
        for _t in ("orders", "lines"):
            if _t in frames and len(frames[_t]):
                _dv = pd.to_datetime(frames[_t]["_date"], errors="coerce").dropna()
                if len(_dv):
                    _mins.append(_dv.min())
        if _mins and primary.get("end"):
            _mind = min(_mins)
            if pd.Timestamp(primary["end"]) < _mind:
                add(100, "unanswerable_before_start", "RESULT = 'unanswerable'\n")

    cands.sort(key=lambda c: -c["score"])
    return cands, spans


# ---------------------------------------------------------------------------
# result matching
# ---------------------------------------------------------------------------
def result_matches_gold(result, gold_type, gold_ans, alias):
    if result is None:
        return gold_ans is None or gold_type == "unanswerable"
    if gold_ans is None:
        return str(result).lower() in ("unanswerable", "none", "null", "")
    pred_type, pred_val = infer_type(result)
    if match_answer(pred_type, pred_val, gold_type, gold_ans, alias):
        return True
    # percent: allow numeric result to be interpreted as percent
    if gold_type == "percent":
        try:
            return abs(round(float(result), 6) - float(str(gold_ans).rstrip("%"))) <= 0.01
        except (TypeError, ValueError):
            pass
    return False


# ---------------------------------------------------------------------------
# execution namespace
# ---------------------------------------------------------------------------
def make_namespace(biz_data, asof, spec):
    """Build canonical frames once and return an exec namespace."""
    from agent import exec_code  # reuse the tested helpers by running prepare once

    prep = render_prepare(spec)
    prep += (
        "\nRESULT = dict(orders=orders, lines=lines, products=products, stock=stock,"
        " purchases=purchases, purchase_lines=purchase_lines, payments=payments,"
        " price_history=price_history, customers=customers, deliveries=deliveries,"
        " lots=lots, lot_sales=lot_sales, stock_tx=stock_tx, conversions=conversions)\n"
    )
    frames = exec_code(prep, biz_data, asof)
    return frames


def run_intent(code, frames):
    ns = {
        "pd": pd,
        "RESULT": None,
        "orders": frames["orders"],
        "lines": frames["lines"],
        "products": frames["products"],
        "stock": frames["stock"],
        "purchases": frames["purchases"],
        "payments": frames["payments"],
        "price_history": frames["price_history"],
        "customers": frames["customers"],
        "deliveries": frames["deliveries"],
        "purchase_lines": frames.get("purchase_lines", pd.DataFrame()),
        "lots": frames.get("lots", pd.DataFrame()),
        "lot_sales": frames.get("lot_sales", pd.DataFrame()),
        "stock_tx": frames.get("stock_tx", pd.DataFrame()),
        "conversions": frames.get("conversions", pd.DataFrame()),
        "normalize_text": norm_name,
        "_re": __import__("re"),
        "vn_normalize": norm_name,
    }
    exec(compile(code, "<intent>", "exec"), ns)  # noqa: S102
    return ns.get("RESULT")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "sft_selfgen.jsonl"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--biz", default="")
    ap.add_argument("--sample", type=int, default=0, help="only N questions per business")
    ap.add_argument("--start", type=int, default=0)
    args = ap.parse_args()

    split = ROOT / "train"
    rulebook = (split / "rulebook.md").read_text(encoding="utf-8")
    questions = [json.loads(l) for l in open(split / "questions.jsonl", encoding="utf-8") if l.strip()]
    gold = {json.loads(l)["id"]: json.loads(l) for l in open(split / "answers.jsonl", encoding="utf-8") if l.strip()}

    if args.biz:
        questions = [q for q in questions if q["business_id"] == args.biz]
    if args.start:
        questions = questions[args.start:]
    if args.limit:
        questions = questions[: args.limit]

    by_biz: dict[str, list] = {}
    for q in questions:
        by_biz.setdefault(q["business_id"], []).append(q)

    records = []
    stats = {"ok": 0, "fail": 0, "exec_err": 0, "no_cand": 0}
    per_type = {}
    per_intent = {}

    for biz, qs in sorted(by_biz.items()):
        if args.sample:
            qs = qs[: args.sample]
        biz_dir = split / "data" / biz
        raw = _SPECS_RAW.get(biz)
        if raw is None:
            print(f"!! no spec for {biz}", flush=True)
            continue
        biz_data = load_business(biz_dir)
        spec = build_spec(biz_data, raw)
        frames = make_namespace(biz_data, qs[0]["as_of_date"], spec)
        prods, cats = build_match_lists(frames)
        GLOBAL_CTX.update(frames)
        biz_schema = describe_business(biz_dir)
        data_keys = [k for k in biz_data if not k.startswith("_")]

        ok_b = 0
        for q in qs:
            g = gold[q["id"]]
            gt, ga = g["type"], g["answer"]
            cands, spans = gen_candidates(q["question"], q["as_of_date"], spec, frames, prods, cats)
            if not cands:
                stats["no_cand"] += 1
                continue
            matched = False
            for c in cands[:8]:
                try:
                    res = run_intent(c["code"], frames)
                except Exception:
                    stats["exec_err"] += 1
                    continue
                if result_matches_gold(res, gt, ga, g.get("alias", [])):
                    # ---- emit ----
                    prompt = build_prompt(
                        q["question"], q["as_of_date"], biz_schema, rulebook[:2000], data_keys
                    )
                    full_code = render_prepare(spec) + "\n" + c["code"]
                    records.append({
                        "id": q["id"],
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                            {"role": "assistant", "content": f"```python\n{full_code.strip()}\n```"},
                        ],
                        "gold_type": gt,
                        "gold_answer": ga,
                        "biz_id": biz,
                        "intent": c["intent"],
                        "span": spans[0]["label"] if spans else "all",
                    })
                    matched = True
                    ok_b += 1
                    stats["ok"] += 1
                    per_type[gt] = per_type.get(gt, 0) + 1
                    per_intent[c["intent"]] = per_intent.get(c["intent"], 0) + 1
                    break
            if not matched:
                stats["fail"] += 1
        print(f"{biz}: {ok_b}/{len(qs)} verified", flush=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("\n=== summary ===")
    print("stats:", stats)
    print("per_type:", dict(sorted(per_type.items())))
    print("per_intent:", dict(sorted(per_intent.items(), key=lambda kv: -kv[1])))
    print(f"wrote {len(records)} -> {out}")


if __name__ == "__main__":
    main()
