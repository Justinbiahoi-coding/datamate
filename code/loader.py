"""Load all data files for a business into DataFrames.

Usage:
    from loader import load_business
    data = load_business(split_root / "data" / biz_id)
    # data["ban_hang"]  → DataFrame
    # data["_readme"]   → str (README.md content)
    # data["_files"]    → list of file paths loaded
"""
import sqlite3
from pathlib import Path
from functools import lru_cache

try:
    import pandas as pd
    import openpyxl  # noqa: F401 — ensure Excel support
except ImportError as e:
    raise ImportError(f"pip install pandas openpyxl: {e}")



def _read_sheet_smart(xl, sheet_name, max_skip=5) -> "pd.DataFrame":
    """Read sheet, auto-detect real header row by skipping title rows."""
    for skip in range(0, max_skip + 1):
        df = pd.read_excel(xl, sheet_name=sheet_name, header=0, skiprows=skip if skip else None)
        unnamed = sum(1 for c in df.columns if str(c).startswith("Unnamed:"))
        # If >50% unnamed cols, likely not the header row yet
        if unnamed / max(len(df.columns), 1) < 0.5:
            return df
    # fallback: return with skip=0
    return pd.read_excel(xl, sheet_name=sheet_name, header=0)


@lru_cache(maxsize=64)
def load_business(biz_dir: Path) -> dict:
    """Return dict of name→DataFrame (or str for _readme)."""
    biz_dir = Path(biz_dir)
    result = {"_files": [], "_readme": ""}

    readme = biz_dir / "README.md"
    if readme.exists():
        result["_readme"] = readme.read_text(encoding="utf-8")

    for path in sorted(biz_dir.iterdir()):
        if path.name == "README.md" or path.name.startswith("."):
            continue

        suffix = path.suffix.lower()
        stem = path.stem

        if suffix == ".csv":
            df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
            result[stem] = df
            result["_files"].append(str(path))

        elif suffix in (".xlsx", ".xls"):
            xl = pd.ExcelFile(path)
            if len(xl.sheet_names) == 1:
                df = _read_sheet_smart(xl, 0)
                result[stem] = df
            else:
                sheets = {}
                for sname in xl.sheet_names:
                    try:
                        df = _read_sheet_smart(xl, sname)
                        sheets[sname] = df
                    except Exception:
                        pass
                result[stem] = sheets
                dfs = list(sheets.values())
                if dfs and all(list(d.columns) == list(dfs[0].columns) for d in dfs):
                    result[stem + "__all"] = pd.concat(dfs, ignore_index=True)
            result["_files"].append(str(path))

        elif suffix == ".sqlite":
            con = sqlite3.connect(path)
            tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", con)
            for tname in tables["name"]:
                result[tname] = pd.read_sql(f"SELECT * FROM [{tname}]", con)
            con.close()
            result["_files"].append(str(path))

    return result


_STATUS_KEYWORDS = {"status", "trạng", "trangthai", "trangThai", "ghi", "ghichu", "loai", "loại", "type"}


def _ffill_hint(df, threshold=0.3) -> str:
    """Detect grouped-row format: first col has >30% NaN but other cols have data → need ffill."""
    if len(df) < 10:
        return ""
    first_col = df.columns[0]
    nan_ratio = df[first_col].isna().mean()
    # Also check if a date/status column has NaN gaps while product columns don't
    has_id_gaps = nan_ratio > threshold
    if has_id_gaps:
        return f" ⚠️ GROUPED ROWS: '{first_col}' has {nan_ratio:.0%} NaN — call df[header_cols].ffill() before filtering (header_cols = non-NaN columns in first row)"
    return ""


def _col_hints(df, max_sample=4) -> str:
    """Return hints: sample for first columns, unique values for all status/categorical columns."""
    hints = []
    status_keywords = {"status", "trang", "trạng", "ghi", "loai", "loại"}
    all_cols = list(df.columns)

    # First pass: find ALL status columns anywhere in the df
    for col in all_cols:
        s = df[col].dropna()
        if s.empty:
            continue
        col_lower = col.lower().replace(" ", "")
        if any(kw in col_lower for kw in status_keywords) and s.nunique() <= 15:
            uniq = sorted(str(v) for v in s.unique()[:10])
            hints.append(f"{col}∈{uniq}")

    # Second pass: sample values for first non-status columns
    sample_count = 0
    for col in all_cols[:max_sample + 2]:
        col_lower = col.lower().replace(" ", "")
        if any(kw in col_lower for kw in status_keywords):
            continue  # already handled above
        s = df[col].dropna()
        if s.empty or sample_count >= max_sample:
            continue
        hints.append(f"{col}='{s.iloc[0]}'")
        sample_count += 1

    return f" [{', '.join(hints)}]" if hints else ""


def describe_business(biz_dir: Path) -> str:
    """Return schema summary for LLM context, with actual variable names."""
    import pandas as pd
    data = load_business(Path(biz_dir))
    lines = [f"# Business: {Path(biz_dir).name}"]
    if data["_readme"]:
        lines.append("\n## README\n" + data["_readme"][:600])
    lines.append("\n## Available variables (use these exact names in code)")
    for key, val in data.items():
        if key.startswith("_"):
            continue
        if isinstance(val, dict):  # multi-sheet
            sheets_info = []
            for sheet, df in val.items():
                safe = sheet.replace(" ", "_").replace("/", "_").replace("-", "_").replace(".", "_")
                var = f"{key}__{safe}"
                date_hint = ""
                for col in df.columns:
                    sample = df[col].dropna().head(1)
                    if not sample.empty and any(k in col.lower() for k in ("ngay", "thoi", "date", "time", "gio")):
                        date_hint = f" [e.g. {col}='{sample.iloc[0]}']"
                        break
                sheets_info.append(f"  - `{var}`: {len(df)} rows, cols: {list(df.columns)[:8]}{date_hint}")
            lines.append(f"- `{key}` (multi-sheet dict), merged=`{key}__all`:")
            lines.extend(sheets_info)
        else:
            ffill_hint = _ffill_hint(val)
            lines.append(f"- `{key}`: {len(val)} rows, cols: {list(val.columns)}{_col_hints(val)}{ffill_hint}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python loader.py <biz_dir>")
        sys.exit(1)
    print(describe_business(Path(sys.argv[1])))
