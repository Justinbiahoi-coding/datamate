"""Prompt v2: one prompt format for SFT data AND inference (train/serve must match).

Differences from v1 (agent.SYSTEM_PROMPT / build_prompt):
- short system prompt that does not contradict the rulebook (v1 told the model to use
  cancellation_rate()/find_revenue_col() shortcuts that violate rulebook §1)
- full README (v1 cut it to 600 chars)
- full rulebook, minus the submission-format preamble (v1 cut it to the first 2000 chars)
- repeated per-month sheet listings compressed into one line
- rulebook comes first, so it is a shared prefix across questions (prefix-cache friendly)
"""
import re
from functools import lru_cache
from pathlib import Path

from loader import load_business, _col_hints, _ffill_hint

SYSTEM_PROMPT_V2 = """\
You are a data analyst. Given a Vietnamese business question, the rulebook and a description of the business data, \
write Python (pandas) code that computes the answer and store it in RESULT.

How the code runs
- Every table is already loaded as a pandas DataFrame variable (exact names under "Business data"); `data` is a dict of the same tables. \
Never read files. Call .copy() before modifying a DataFrame.
- Multi-sheet Excel: the merged table is `<name>__all`; one sheet is `<name>__<sheet>` (spaces, dashes and dots become `_`).
- Helpers: to_num(series) parses money strings ('1,234', '45k', '1tr575'); parse_date(series) parses dates (ISO, dd/mm/yyyy, 'D thg M YYYY', Excel serials); \
vn_normalize(text) lowercases and strips Vietnamese accents; get_month_df(stem, year, month) returns one month's sheet.
- `as_of_date` is a 'YYYY-MM-DD' string meaning today. Allowed imports: pandas, numpy, re, unicodedata, math, datetime.

Answer rules
- Follow the rulebook exactly. If the question itself says otherwise, the question wins.
- RESULT types: number (int/float; money is an integer number of VND), percent (string like '12.34%', 2 decimals), \
date ('YYYY-MM-DD', or 'YYYY-MM' when the question is about a month), boolean, string (spelled exactly as in the data), \
list (ordered Python list), table (dict {'columns': [...], 'rows': [[...], ...]}).
- RESULT = "unanswerable" when the data cannot support the question (see the rulebook).
- Do not print. Only assign RESULT.
"""


def select_rules(rulebook: str) -> str:
    """Full rulebook minus the submission-format preamble/table of the scoring section."""
    lines = rulebook.splitlines()
    out, skipping = [], False
    for ln in lines:
        if re.match(r"^##\s+\d*\.?\s*.*(đáp án|chấm điểm)", ln, re.I):
            out.append(ln)
            skipping = True
            continue
        if skipping:
            if ln.startswith("Đúng format rồi") or re.match(r"^##\s", ln):
                skipping = False
            else:
                continue
        out.append(ln)
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _safe(sheet) -> str:
    return str(sheet).replace(" ", "_").replace("/", "_").replace("-", "_").replace(".", "_")


@lru_cache(maxsize=None)
def describe_business_v2(biz_dir: str, readme_cap: int = 9000) -> str:
    data = load_business(Path(biz_dir))
    lines = [f"# Business: {Path(biz_dir).name}"]
    if data.get("_readme"):
        lines.append("\n## README\n" + data["_readme"][:readme_cap].strip())
    lines.append("\n## Available variables (use these exact names in code)")
    for key, val in data.items():
        if key.startswith("_"):
            continue
        if isinstance(val, dict):
            groups = {}
            for sheet, df in val.items():
                groups.setdefault(tuple(str(c) for c in df.columns), []).append((f"{key}__{_safe(sheet)}", len(df)))
            lines.append(f"- `{key}` (multi-sheet dict); merged table = `{key}__all`; sheet variables:")
            for cols, items in groups.items():
                if len(items) == 1:
                    name = f"`{items[0][0]}` ({items[0][1]} rows)"
                else:
                    name = f"`{items[0][0]}` ... `{items[-1][0]}` ({len(items)} sheets, {sum(n for _, n in items)} rows in total)"
                lines.append(f"  - {name}, cols: {list(cols)}")
        else:
            lines.append(f"- `{key}`: {len(val)} rows, cols: {list(val.columns)}{_col_hints(val)}{_ffill_hint(val)}")
    return "\n".join(lines)


def build_user_prompt_v2(question: str, as_of_date: str, schema: str, rules: str) -> str:
    return (
        f"## Rulebook (default rules; the question overrides them)\n{rules}\n\n"
        f"## Business data\n{schema}\n\n"
        f"## Question\n{question}\n\n"
        f"## as_of_date\n{as_of_date}\n\n"
        "Write the pandas code. Assign the answer to RESULT.\n```python\n"
    )


def prompt_for(item: dict, split_root: Path, rulebook: str):
    """(system, user) for one question item."""
    schema = describe_business_v2(str(Path(split_root) / "data" / item["business_id"]))
    return SYSTEM_PROMPT_V2, build_user_prompt_v2(item["question"], item["as_of_date"], schema, select_rules(rulebook))


# ── v3: same layout as v2, plus value/date profiles and a correct helper list ──────────────
SYSTEM_PROMPT_V3 = SYSTEM_PROMPT_V2.replace(
    "- Helpers: to_num(series) parses money strings ('1,234', '45k', '1tr575'); parse_date(series)",
    "- Helpers: money(x) parses Vietnamese money, scalar or Series ('1.200.000đ', '1,200,000', '25,000.0000', '129 000', "
    "'41k', '2tr900', '16,56tr'): use it for every money column. to_num(series) is for plain numbers only. parse_date(series)",
).replace("Allowed imports: pandas, numpy, re, unicodedata, math, datetime.",
          "Allowed imports: pandas, numpy, re, unicodedata, math, datetime, decimal. Do not define functions.")
assert SYSTEM_PROMPT_V3 != SYSTEM_PROMPT_V2 and "money(x)" in SYSTEM_PROMPT_V3

_DATE_WORDS = ("ngày", "ngay", "thời gian", "thoi gian", "date", "time", "giờ", "gio", "thời điểm")


def _date_range(s):
    import pandas as pd
    s = s.dropna()
    if s.empty:
        return None
    if pd.api.types.is_datetime64_any_dtype(s):
        d = s
    else:
        t = s.astype(str).str.strip()
        num = pd.to_numeric(t, errors="coerce")
        if num.notna().mean() > 0.9 and num.between(20000, 80000).mean() > 0.9:
            d = pd.Timestamp("1899-12-30") + pd.to_timedelta(num, unit="D")
        elif t.str.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}").mean() > 0.5:
            d = pd.to_datetime(t.str.replace("/", "-", regex=False), yearfirst=True, errors="coerce")
        else:
            d = pd.to_datetime(t, dayfirst=True, errors="coerce")
    d = d.dropna()
    if len(d) < 0.8 * len(s):
        return None
    return f"{d.min():%Y-%m-%d}..{d.max():%Y-%m-%d}"


def _profile(df, max_vals: int = 12) -> list:
    """Low-cardinality text columns with all values and counts; date columns with their range."""
    out = []
    for col in df.columns:
        s = df[col].dropna()
        if s.empty:
            continue
        name = str(col).lower()
        if any(w in name for w in _DATE_WORDS):
            r = _date_range(s)
            if r:
                out.append(f"{col}: {r}")
                continue
        if s.dtype == object:
            vc = s.astype(str).str.strip().value_counts()
            if len(vc) <= max_vals and len(vc) < 0.5 * len(s):
                out.append(f"{col}: " + ", ".join(f"{str(v)[:30]}×{n}" for v, n in vc.items()))
    return out


@lru_cache(maxsize=None)
def describe_business_v3(biz_dir: str, readme_cap: int = 9000) -> str:
    import pandas as pd
    data = load_business(Path(biz_dir))
    lines = [f"# Business: {Path(biz_dir).name}"]
    if data.get("_readme"):
        lines.append("\n## README\n" + data["_readme"][:readme_cap].strip())
    lines.append("\n## Available variables (use these exact names in code)")
    for key, val in data.items():
        if key.startswith("_"):
            continue
        if isinstance(val, dict):
            groups = {}
            for sheet, df in val.items():
                groups.setdefault(tuple(str(c) for c in df.columns), []).append((f"{key}__{_safe(sheet)}", df))
            lines.append(f"- `{key}` (multi-sheet dict); merged table = `{key}__all`; sheet variables:")
            for cols, items in groups.items():
                n = sum(len(d) for _, d in items)
                name = f"`{items[0][0]}` ({n} rows)" if len(items) == 1 else \
                    f"`{items[0][0]}` ... `{items[-1][0]}` ({len(items)} sheets, {n} rows in total)"
                lines.append(f"  - {name}, cols: {list(cols)}{_ffill_hint(items[0][1])}")
                lines += [f"    · {p}" for p in _profile(pd.concat([d for _, d in items], ignore_index=True))]
        else:
            lines.append(f"- `{key}`: {len(val)} rows, cols: {list(val.columns)}{_ffill_hint(val)}")
            lines += [f"  · {p}" for p in _profile(val)]
    return "\n".join(lines)


def build_versioned_prompt(version: str, question: str, as_of_date: str, biz_dir, rulebook: str):
    """(system, user) for prompt v2 or v3. Single source of truth for SFT data and inference."""
    if version == "v3":
        return SYSTEM_PROMPT_V3, build_user_prompt_v2(question, as_of_date, describe_business_v3(str(biz_dir)), select_rules(rulebook))
    if version == "v2":
        return SYSTEM_PROMPT_V2, build_user_prompt_v2(question, as_of_date, describe_business_v2(str(biz_dir)), select_rules(rulebook))
    raise ValueError(f"unknown prompt version {version!r}")
