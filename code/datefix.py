"""Make relative-date solutions compute their dates from as_of_date instead of hardcoding literals.

A solution for "hôm nay / tuần trước / tháng này / 30 ngày gần nhất ..." that contains '2025-08-12' forces the model to do
calendar arithmetic in its head. This rewrites such literals into expressions of as_of_date, but only when it is unambiguous:
- the question has at least one relative cue,
- every date literal in the code is an allowed relation for that cue,
- running the new code at the original as_of_date gives exactly the stored answer.
"""
import re, unicodedata, datetime as dt


def _na(s):
    return unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()


# cue regex -> allowed relations
CUES = [
    (r"\bhom nay\b|\btoi nay\b", {"as_of"}),
    (r"\bhom qua\b|\bbua qua\b|\btoi qua\b", {"yesterday"}),
    (r"\btuan truoc\b|\btuan roi\b", {"monday_last", "sunday_last"}),
    (r"\btuan nay\b", {"monday_this", "as_of"}),
    (r"\bthang nay\b", {"month_start", "as_of"}),
    (r"\bthang truoc\b|\bthang roi\b", {"prev_month_start", "prev_month_end"}),
    (r"\b(\d+) ngay (gan nhat|qua|vua qua)\b", {"as_of"}),  # handled specially for N-day windows
    (r"\bdau nam\b|\bnam nay\b", {"year_start", "as_of"}),
    (r"\bden het hom nay\b|\btinh den hom nay\b", {"as_of"}),
]

EXPR = {
    "as_of": "_asof.strftime('%Y-%m-%d')",
    "yesterday": "(_asof - pd.Timedelta(days=1)).strftime('%Y-%m-%d')",
    "month_start": "_asof.replace(day=1).strftime('%Y-%m-%d')",
    "prev_month_start": "(_asof.replace(day=1) - pd.offsets.MonthBegin(1)).strftime('%Y-%m-%d')",
    "prev_month_end": "(_asof.replace(day=1) - pd.Timedelta(days=1)).strftime('%Y-%m-%d')",
    "monday_this": "(_asof - pd.Timedelta(days=_asof.weekday())).strftime('%Y-%m-%d')",
    "monday_last": "(_asof - pd.Timedelta(days=_asof.weekday() + 7)).strftime('%Y-%m-%d')",
    "sunday_last": "(_asof - pd.Timedelta(days=_asof.weekday() + 1)).strftime('%Y-%m-%d')",
    "year_start": "_asof.replace(month=1, day=1).strftime('%Y-%m-%d')",
}

LIT = re.compile(r"""(['"])(\d{4}-\d{2}-\d{2})\1""")


def relations(as_of: str, n_days=None):
    d = dt.date.fromisoformat(as_of)
    first = d.replace(day=1)
    pm_end = first - dt.timedelta(days=1)
    mon = d - dt.timedelta(days=d.weekday())
    R = {
        "as_of": d, "yesterday": d - dt.timedelta(days=1), "month_start": first,
        "prev_month_start": pm_end.replace(day=1), "prev_month_end": pm_end,
        "monday_this": mon, "monday_last": mon - dt.timedelta(days=7), "sunday_last": mon - dt.timedelta(days=1),
        "year_start": d.replace(month=1, day=1),
    }
    out = {}
    for k, v in R.items():
        out.setdefault(v.isoformat(), []).append(k)
    if n_days:
        out.setdefault((d - dt.timedelta(days=n_days - 1)).isoformat(), []).append("nday_start")
    return out


def transform(code: str, as_of: str, question: str):
    """Return new code or None when not safely transformable."""
    if "as_of_date" in code:
        return None
    q = _na(question)
    hit, allowed, n_days = 0, set(), None
    for pat, rel in CUES:
        m = re.search(pat, q)
        if m:
            hit += 1
            allowed |= set(rel)
            if m.groups() and m.group(1).isdigit():
                n_days = int(m.group(1)); allowed |= {"nday_start"}
    if hit == 0:
        return None
    lits = LIT.findall(code)
    if not lits or len(LIT.findall(code)) != len(re.findall(r"\d{4}-\d{2}-\d{2}", code)):
        return None  # a date appears inside a longer string or f-string: leave it
    rel = relations(as_of, n_days)
    chosen = {}
    for _, d in lits:
        cand = [r for r in rel.get(d, []) if r in allowed]
        if len(cand) != 1:
            return None
        chosen[d] = cand[0]

    def sub(m):
        r = chosen[m.group(2)]
        return f"(_asof - pd.Timedelta(days={n_days - 1})).strftime('%Y-%m-%d')" if r == "nday_start" else EXPR[r]

    new = LIT.sub(sub, code)
    head = "" if re.search(r"^\s*import pandas as pd", new, re.M) else "import pandas as pd\n"
    return f"{head}_asof = pd.Timestamp(as_of_date)\n{new}"
