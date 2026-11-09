"""DataMate agent skeleton.

Flow:
  1. Load business data (loader.py)
  2. Build LLM prompt: README + schema + rulebook excerpt + question
  3. LLM generates Python code using pandas
  4. Execute code in sandbox → extract answer
  5. Format answer with correct type

Currently: returns abstain for every question (safe baseline, 0 pts = no loss).
Next step: wire in Qwen2.5-Coder-14B-Instruct via vLLM.

Run:
  python agent.py --split train --out submission.jsonl [--limit 10]
  python agent.py --split public_test --out submission.jsonl
"""
import json
import sys
import argparse
import textwrap
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from loader import load_business, describe_business  # noqa: E402


# ── Sandbox execution ────────────────────────────────────────────────────────

def exec_code(code: str, biz_data: dict, as_of_date: str) -> Any:
    """Execute LLM-generated pandas code; return value of last expression or RESULT variable."""
    import io
    import contextlib
    import pandas as pd  # noqa: F401

    # Inject available DataFrames + helpers into exec scope
    def to_num(series):
        """Convert Vietnamese number strings like '1,234,567' to float."""
        return pd.to_numeric(
            series.astype(str).str.replace(r'[^\d.\-]', '', regex=True),
            errors='coerce'
        )

    def parse_date(series):
        """Parse dates: ISO, dd/mm/yyyy, 'D thg M YYYY' (Vietnamese), Excel serial ints.

        Important: `dayfirst=True` alone mis-parses ISO strings such as
        '2025-03-01' as 2025-01-03. We therefore detect ISO-like values first
        and parse them with yearfirst=True, and only use dayfirst for
        dd/mm/yyyy-style values.
        """
        import pandas as _pd
        import re as _re
        if not isinstance(series, _pd.Series):
            series = _pd.Series(series)

        result = _pd.Series(_pd.NaT, index=series.index, dtype="datetime64[ns]")

        # Excel serial numbers (e.g. 45658) must be converted manually:
        # pd.to_datetime would treat them as nanoseconds since 1970.
        numeric = _pd.to_numeric(series, errors="coerce")
        num_mask = numeric.notna() & (numeric > 1000) & (numeric < 100000)
        if num_mask.any():
            result.loc[num_mask] = _pd.Timestamp("1899-12-30") + _pd.to_timedelta(
                numeric.loc[num_mask], unit="D"
            )

        rest = series.notna() & ~num_mask
        if rest.any():
            s = series.loc[rest].astype(str).str.strip()
            idx = s.index

            # ISO-like: YYYY-MM-DD / YYYY/MM/DD (optionally with time)
            iso_mask = s.str.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", na=False)
            if iso_mask.any():
                iso = _pd.to_datetime(
                    s[iso_mask].str.replace("/", "-", regex=False),
                    yearfirst=True, errors="coerce",
                )
                result.loc[idx[iso_mask]] = iso

            # dd/mm/yyyy or dd-mm-yyyy
            dmy_mask = ~iso_mask & s.str.match(r"^\d{1,2}[-/]\d{1,2}[-/]\d{4}", na=False)
            if dmy_mask.any():
                dmy = _pd.to_datetime(s[dmy_mask], dayfirst=True, errors="coerce")
                result.loc[idx[dmy_mask]] = dmy

            # Vietnamese: "1 thg 5 2026"
            vn_mask = ~iso_mask & ~dmy_mask & s.str.contains(r"thg", case=False, regex=True, na=False)
            if vn_mask.any():
                def _parse_vn(x):
                    m = _re.match(r"(\d+)\s+thg\s+(\d+)\s+(\d{4})", x, _re.IGNORECASE)
                    if m:
                        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                        try:
                            return _pd.Timestamp(y, mo, d)
                        except Exception:
                            pass
                    return _pd.NaT
                result.loc[idx[vn_mask]] = s[vn_mask].apply(_parse_vn)

            # Fallback for anything else
            other = ~iso_mask & ~dmy_mask & ~vn_mask
            if other.any():
                result.loc[idx[other]] = _pd.to_datetime(s[other], dayfirst=True, errors="coerce")

        return result

    # Build augmented data dict (includes sub-sheet keys so data["stem__sheet"] works)
    data_augmented: dict = {}
    local_ns: dict = {
        "pd": pd,
        "as_of_date": as_of_date,
        "RESULT": None,
        "to_num": to_num,
        "parse_date": parse_date,
    }
    for k, v in biz_data.items():
        if k.startswith("_"):
            continue
        data_augmented[k] = v
        local_ns[k] = v
        if isinstance(v, dict):  # multi-sheet: expose sheet-level in both dict and namespace
            for sheet, df in v.items():
                safe = sheet.replace(" ", "_").replace("/", "_").replace("-", "_").replace(".", "_")
                sub_key = f"{k}__{safe}"
                data_augmented[sub_key] = df
                local_ns[sub_key] = df
    local_ns["data"] = data_augmented

    def get_month_df(stem: str, year: int, month: int):
        """Find sheet DataFrame for a specific year-month. Use when exact key name is uncertain."""
        import unicodedata
        def normalize(s):
            return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode().lower()
        y, m = str(year), f"{month:02d}"
        for k, v in data_augmented.items():
            kn = normalize(k)
            if normalize(stem) in kn and y in kn and m in kn and k != stem and k != f"{stem}__all":
                return v
        # fallback: use __all filtered by date
        all_key = f"{stem}__all"
        if all_key in data_augmented:
            df = data_augmented[all_key]
            for col in df.columns:
                if any(x in col.lower() for x in ('ngay', 'thoi', 'date', 'gio')):
                    dates = parse_date(df[col])
                    mask = (dates.dt.year == year) & (dates.dt.month == month)
                    return df[mask]
        return None

    local_ns["get_month_df"] = get_month_df

    def find_revenue_col(df):
        """Return the best available revenue column name, in priority order."""
        for col in ['Tổng tiền hàng', 'Thành tiền', 'Tổng tiền', 'Doanh thu', 'Tiền hàng',
                    'Thanh tien', 'thanh_tien', 'Tong tien', 'tong_tien']:
            if col in df.columns:
                return col
        return None

    local_ns["find_revenue_col"] = find_revenue_col

    def normalize_text(s):
        """Strip accents, collapse whitespace, lowercase for Vietnamese string matching."""
        import unicodedata as _ud, re as _re
        s = _ud.normalize('NFD', str(s)).encode('ascii', 'ignore').decode().lower()
        return _re.sub(r'\s+', ' ', s).strip()

    local_ns["normalize_text"] = normalize_text
    local_ns["vn_normalize"] = normalize_text  # alias — use this to avoid accidental shadowing

    def join_by_name(left_df, left_col, right_df, right_col, right_val_col):
        """Map left_df[left_col] to right_df[right_val_col] via normalized name matching."""
        right_map = {normalize_text(k): str(v).strip()
                     for k, v in zip(right_df[right_col], right_df[right_val_col])
                     if pd.notna(k)}
        return left_df[left_col].apply(normalize_text).map(right_map)

    local_ns["join_by_name"] = join_by_name

    def cancellation_rate(df, order_id_col, status_col):
        """Cancellation rate: cancelled/(total - returned) × 100, returns '1.21%' format.
        Numerator: orders with 'hủy|huỷ'. Denominator: ALL orders EXCEPT 'Đã trả hàng'."""
        mask_cancel = df[status_col].str.contains('hủy|huỷ', case=False, na=False)
        mask_returned = df[status_col].str.contains('Đã trả hàng', case=False, na=False)
        cancelled = df[mask_cancel][order_id_col].nunique()
        total = df[~mask_returned][order_id_col].nunique()
        return f"{round(cancelled / total * 100, 2):.2f}%"

    local_ns["cancellation_rate"] = cancellation_rate

    def get_rx_product_names(drug_df, sp_df):
        """Return set of normalized product names for prescription drugs (Thuốc kê đơn==True)."""
        def norm_sku(s):
            s = str(s).strip()
            try:
                f = float(s)
                return str(int(f)) if f == int(f) else s
            except Exception:
                return s.lower()

        rx_mask = drug_df['Thuốc kê đơn'].apply(
            lambda x: str(x).strip().lower() in ('true', '1', 'yes', 'có', 'x')
            or x is True
        )
        rx_skus = set(norm_sku(s) for s in drug_df[rx_mask]['Mã SKU'] if pd.notna(s))
        if not rx_skus:
            return set()
        sp_norm_sku = sp_df['Mã SKU'].apply(norm_sku)
        rx_sp = sp_df[sp_norm_sku.isin(rx_skus)]['Tên sản phẩm']
        return set(rx_sp.apply(normalize_text))

    local_ns["get_rx_product_names"] = get_rx_product_names

    stdout_buf = io.StringIO()
    with contextlib.redirect_stdout(stdout_buf):
        exec(compile(code, "<llm_code>", "exec"), local_ns)  # noqa: S102

    return local_ns.get("RESULT")


# ── Prompt building ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""\
You are a data analyst. Given a Vietnamese business question and pandas DataFrames,
write Python code that computes the answer. Store the final answer in RESULT.

Rules:
- RESULT must be one of:
  * number: int or float (e.g. RESULT = 89526400)
  * percent: string ending with '%' (e.g. RESULT = '2.08%') — use for tỉ lệ/% questions
  * date: string YYYY-MM-DD (e.g. RESULT = '2025-06-01')
  * string: text answer
  * list: Python list
  * dict with keys 'columns' and 'rows': for table answers
- Set RESULT = "unanswerable" if the data cannot support the question.
- Do NOT print; just assign RESULT.
- Use as_of_date (string YYYY-MM-DD) for all relative time expressions.
- Variable `data` is a dict mapping name→DataFrame (or name→dict-of-sheets for multi-sheet Excel).
- Single-sheet files: accessible as variable (e.g. `ban_hang`, `DanhSachNhapHang`).
- Multi-sheet files: `SoBanHang_1` is a dict {sheet_name: df}; merged version is `SoBanHang_1__all`.
  Individual sheets available as direct variables: `SoBanHang_1__Thang_06_2025` (spaces/dashes/dots→_).
  Example: sheet "04.2025" → variable `DanhSachHoaDon__04_2025`.
  CORRECT access: `DuLieuXuat__DanhSachThuoc` (direct variable) ✓
  CORRECT access: `DuLieuXuat['DanhSachThuoc']` (dict key = actual sheet name) ✓
  WRONG access: `DuLieuXuat['DuLieuXuat__DanhSachThuoc']` ✗ (keys don't have the stem prefix)
- Use `data.keys()` to see all available tables if unsure.
- Helper `get_month_df(stem, year, month)` finds the right month's DataFrame, e.g.:
  `df = get_month_df("SoBanHang", 2025, 10)` → October 2025 sheet.

Data format notes:
- Number/currency columns may be stored as strings with commas e.g. "1,234,567" or "45k" or "1tr575".
  Use helper: to_num(series) to convert them to float.
- Dates: ALWAYS use parse_date(series) — NEVER use pd.to_datetime(format=...) or strptime directly.
  parse_date() handles: "01/06/2025", "1/6", "1 thg 6 2025", Excel serial integers (e.g. 45689).
- "tháng này" = from day 1 of month(as_of_date) to as_of_date inclusive.
- "tuần rồi/tuần trước" = Mon–Sun of previous week.
- "bán chạy" = by quantity, NOT revenue.

CRITICAL — Revenue column choice:
- Use helper: rev_col = find_revenue_col(df) — returns the best revenue column in this priority:
  `Tổng tiền hàng` > `Thành tiền` > `Tổng tiền` > `Doanh thu` > `Tiền hàng`
- Do NOT use `Tổng sau giảm giá` — it includes delivery/service fees, making it LARGER than
  goods revenue. Never use it for revenue calculation even if it exists alongside `Tổng tiền hàng`.
- Example: rev_col = find_revenue_col(df); total = to_num(df[rev_col]).sum()

- Cancellation rate (tỉ lệ đơn hủy): ALWAYS use the cancellation_rate() helper:
  RESULT = cancellation_rate(df, 'order_id_col', 'status_col')
  — numerator = nunique orders with 'hủy|huỷ'; denominator = ALL EXCEPT 'Đã trả hàng'
  — NEVER compute this manually; the helper handles 'Đã trả hàng' exclusion correctly
  — NEVER use len(df) as denominator (rows ≠ orders in grouped data)
  — NEVER round to 1 decimal; the helper already returns 2 decimal places
  Example (biz_117, Oct 2025 cancellation rate):
    df = get_month_df("SoBanHang", 2025, 10)
    RESULT = cancellation_rate(df, 'Mã phiếu', 'Ghi chú TT')

- Revenue exclusion (excluding cancelled+returned from revenue):
  EXCLUDE both cancelled AND returned: str.contains('hủy|huỷ|hoàn hàng|trả lại|hoàn trả', case=False, na=False)
  NOTE: "trả lại", "Hoàn trả" = returned orders (also excluded from revenue, same rule as cancelled).
  NOTE: "Hoàn thành", "xong", "Đã hoàn thành" means COMPLETED — do NOT exclude it.
  Look in columns: Trạng thái, Ghi chú TT, GhiChu, TrangThai, Status.
  Count DISTINCT orders (by Mã hóa đơn, Mã phiếu, order_id), not rows.

- When a table has BOTH an order-level header (DanhSachHoaDon, BanHang_HoaDon…) AND line-item detail
  (DanhSachHoaDonChiTiet, BanHang_ChiTietHoaDon…), prefer the order-level header for total revenue.
  find_revenue_col(DanhSachHoaDon) returns 'Tổng tiền hàng' — use that column.

- SoQuy (cash register log): amounts like "90.000đ" use Vietnamese dot-thousands format.
  to_num() CANNOT parse this correctly — it gives 90.0 instead of 90,000.
  Parse SoQuy.Giá trị with: series.str.replace('đ','').str.replace('.','').astype(float)

- For specific month queries, use the INDIVIDUAL sheet variable for that month. Check the schema
  for the EXACT variable name (may have Vietnamese accents like `SoBanHang__Tháng_10_2025`).
  Use `get_month_df("SoBanHang", 2025, 10)` as a safe alternative that handles accent variations.
  Use `stem__all` only when no specific sheet exists or the question spans multiple months.

- Prescription drugs (thuốc kê đơn): look for boolean column `Thuốc kê đơn` in drug table.
  Use get_rx_product_names(drug_df, sp_df) + vn_normalize for matching (vn_normalize strips
  Vietnamese accents — NEVER redefine normalize_text locally, use vn_normalize instead).

- GROUPED ROWS (⚠️ in schema): multiple product rows per order; only FIRST row has order header
  (ID/date/status); continuation rows are NaN. Essential steps:
  1. ffill order-level header cols before any filtering:
     order_cols = [c for c in df.columns if df[c].isna().mean() > 0.3]
     df[order_cols] = df[order_cols].ffill()
  2. Filter by date and status AFTER ffill
  3. Count DISTINCT orders: df['Mã đơn hàng'].nunique() — NEVER use len(df) as order count
  4. For order revenue: group by order ID, then SUM line-item totals:
     order_rev = df.groupby('Mã đơn hàng')['Tổng tiền'].sum()
     (product columns like 'Tổng tiền' have values on EVERY row — no ffill needed for them)

- Percent answers: format as f"{round(value, 2):.2f}%" to ensure 2 decimal places.
  Example: RESULT = f"{round(cancelled/total*100, 2):.2f}%"
""")


def build_prompt(question: str, as_of_date: str, biz_schema: str, rulebook_excerpt: str,
                 data_keys: list = None) -> str:
    keys_section = ""
    if data_keys:
        keys_section = f"\n## Exact variable names available\n{chr(10).join(f'- {k}' for k in data_keys if not k.startswith('_'))}\n"
    return textwrap.dedent(f"""\
        {biz_schema}
        {keys_section}
        ## Key business rules
        {rulebook_excerpt}

        ## Question
        {question}

        ## as_of_date
        {as_of_date}

        Write Python code (pandas) to answer the question. Assign the answer to RESULT.
        Use ONLY variable names from the "Exact variable names available" list above.
        ```python
    """)


def extract_code(llm_output: str) -> str:
    """Pull code block from LLM response."""
    if "```python" in llm_output:
        code = llm_output.split("```python", 1)[1]
        code = code.split("```")[0]
        return code.strip()
    if "```" in llm_output:
        code = llm_output.split("```", 1)[1]
        code = code.split("```")[0]
        return code.strip()
    return llm_output.strip()


# ── Type detection ───────────────────────────────────────────────────────────

def infer_type(value: Any) -> tuple[str, Any]:
    """Guess answer type from value."""
    if value is None or str(value).lower() == "unanswerable":
        return "unanswerable", "unanswerable"
    if isinstance(value, bool):
        return "boolean", value
    if isinstance(value, dict) and "columns" in value and "rows" in value:
        return "table", value
    if isinstance(value, list):
        return "list", value
    if isinstance(value, float):
        # Heuristic: if it looks like a percentage (0-100 range and has decimals)
        # leave type detection to the LLM — default to number
        return "number", round(value, 2)
    if isinstance(value, int):
        return "number", value
    # Try parse as date (YYYY-MM-DD or YYYY-MM)
    import re as _re
    s = str(value).strip()
    if _re.match(r'^\d{4}-\d{2}(-\d{2})?$', s):
        return "date", s
    # Try parse as number
    s = s.rstrip("%")
    try:
        f = float(s.replace(",", ""))
        if str(value).endswith("%"):
            return "percent", round(f, 2)
        return "number", int(f) if f == int(f) else round(f, 2)
    except ValueError:
        pass
    return "string", str(value)


# ── LLM stub (replace with vLLM call) ───────────────────────────────────────

_LOCAL_MODEL = None
_LOCAL_TOKENIZER = None

def call_llm(prompt: str, system: str = SYSTEM_PROMPT, history: list = None) -> str:
    """Call LLM. Backends: 'gemini', 'groq', 'anthropic', 'local'. Default: abstain."""
    import os
    backend = os.environ.get("DATAMATE_LLM_BACKEND", "")
    messages = history or []

    if backend == "local":
        # Offline inference cho Docker submission
        global _LOCAL_MODEL, _LOCAL_TOKENIZER
        if _LOCAL_MODEL is None:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            model_path = os.environ.get("LOCAL_MODEL_PATH", "/app/models/qwen3-8b-datamate")
            _LOCAL_TOKENIZER = AutoTokenizer.from_pretrained(model_path)
            _LOCAL_MODEL = AutoModelForCausalLM.from_pretrained(
                model_path, torch_dtype=torch.bfloat16, device_map="auto",
            )
            _LOCAL_MODEL.eval()
        import torch
        msgs = [{"role": "system", "content": system}] + messages + [{"role": "user", "content": prompt}]
        text = _LOCAL_TOKENIZER.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        _device = next(_LOCAL_MODEL.parameters()).device
        inputs = _LOCAL_TOKENIZER(text, return_tensors="pt").to(_device)
        with torch.no_grad():
            out = _LOCAL_MODEL.generate(**inputs, max_new_tokens=2000, temperature=0.3, do_sample=True, pad_token_id=_LOCAL_TOKENIZER.eos_token_id)
        return _LOCAL_TOKENIZER.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)


    if backend == "gemini":
        import time as _time
        from google import genai as _genai
        client = _genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        contents = [{"role": "user" if m["role"] == "user" else "model",
                     "parts": [{"text": m["content"]}]} for m in messages]
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        import signal as _signal
        def _timeout_handler(signum, frame):
            raise TimeoutError("Gemini API timeout")

        for _retry in range(5):
            try:
                _signal.signal(_signal.SIGALRM, _timeout_handler)
                _signal.alarm(120)  # 2 phút timeout mỗi call
                try:
                    resp = client.models.generate_content(
                        model=os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite"),
                        contents=contents,
                        config={"system_instruction": system, "max_output_tokens": 2000, "temperature": 0.3},
                    )
                finally:
                    _signal.alarm(0)
                return resp.text
            except Exception as _e:
                if _retry < 4 and ("503" in str(_e) or "UNAVAILABLE" in str(_e) or "429" in str(_e) or "timeout" in str(_e).lower()):
                    _time.sleep(30 * (_retry + 1))
                    continue
                raise

    if backend == "anthropic":
        import anthropic as _anthropic
        client = _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msgs = [{"role": m["role"], "content": m["content"]} for m in messages]
        msgs.append({"role": "user", "content": prompt})
        resp = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=2000,
            temperature=0.3,
            system=system,
            messages=msgs,
        )
        return resp.content[0].text

    if backend == "ollama":
        # Local Qwen qua Ollama (không cần API key)
        from openai import OpenAI
        client = OpenAI(
            api_key="ollama",
            base_url=os.environ.get("OLLAMA_URL", "http://localhost:11434/v1"),
        )
        msgs = [{"role": "system", "content": system}] + messages + [{"role": "user", "content": prompt}]
        resp = client.chat.completions.create(
            model=os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:14b"),
            messages=msgs, max_tokens=2000, temperature=0.3,
        )
        return resp.choices[0].message.content

    if backend == "groq":
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")
        msgs = [{"role": "system", "content": system}] + messages + [{"role": "user", "content": prompt}]
        resp = client.chat.completions.create(
            model=os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b"),
            messages=msgs, max_tokens=900, temperature=0.3,
        )
        return resp.choices[0].message.content

    return ""  # abstain


# ── Per-question inference ────────────────────────────────────────────────────

def infer(item: dict, split_root: Path, rulebook: str, max_retries: int = 2) -> dict:
    qid = item["id"]
    biz_id = item["business_id"]
    question = item["question"]
    as_of_date = item["as_of_date"]

    biz_dir = split_root / "data" / biz_id

    try:
        biz_data = load_business(biz_dir)
        biz_schema = describe_business(biz_dir)
    except Exception as e:
        return {"id": qid, "type": "abstain", "answer": None, "_err": str(e)}

    import os as _os
    if _os.environ.get("DATAMATE_PROMPT", "v2") == "v2":
        from prompt_v2 import SYSTEM_PROMPT_V2, describe_business_v2, build_user_prompt_v2, select_rules
        system = SYSTEM_PROMPT_V2
        prompt = build_user_prompt_v2(question, as_of_date, describe_business_v2(str(biz_dir)), select_rules(rulebook))
    else:
        system = SYSTEM_PROMPT
        data_keys = [k for k in biz_data if not k.startswith("_")]
        prompt = build_prompt(question, as_of_date, biz_schema, rulebook[:2000], data_keys)

    history = []
    last_code = ""
    last_err = None

    for attempt in range(max_retries + 1):
        if attempt > 0 and last_err:
            history.append({"role": "assistant", "content": f"```python\n{last_code}\n```"})
            history.append({"role": "user", "content": f"Error: {last_err}\nFix the code."})
            current_prompt = ""
        else:
            current_prompt = prompt

        llm_output = call_llm(current_prompt, system=system, history=history)
        if not llm_output.strip():
            return {"id": qid, "type": "abstain", "answer": None}

        last_code = extract_code(llm_output)

        try:
            result = exec_code(last_code, biz_data, as_of_date)
            ans_type, ans_val = infer_type(result)
            return {"id": qid, "type": ans_type, "answer": ans_val, "_code": last_code}
        except Exception as exc:
            last_err = str(exc)[:300]

    return {"id": qid, "type": "abstain", "answer": None, "_err": last_err, "_code": last_code}


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["train", "public_test"], default="public_test")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--out", default="submission.jsonl")
    parser.add_argument("--limit", type=int, default=None, help="Process only N questions")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N questions")
    parser.add_argument("--save-code", action="store_true",
                        help="Lưu _code đã sinh (dùng cho make_sft.py)")
    args = parser.parse_args()

    base = Path(args.data_dir) if args.data_dir else ROOT
    split_map = {
        "train": base / "train",
        "public_test": base / "infor" / "data" / "public_test",
    }
    split_root = split_map[args.split]

    if not split_root.exists():
        print(f"Split root not found: {split_root}")
        sys.exit(1)

    rulebook = (split_root / "rulebook.md").read_text(encoding="utf-8")

    questions_path = split_root / "questions.jsonl"
    with open(questions_path, encoding="utf-8") as f:
        questions = [json.loads(line) for line in f if line.strip()]

    if args.offset:
        questions = questions[args.offset :]
    if args.limit:
        questions = questions[: args.limit]

    out_path = Path(args.out)
    n_abstain = n_answered = 0

    # Resume: skip câu đã trả lời trong lần chạy trước
    done_ids = set()
    if out_path.exists():
        with open(out_path, encoding="utf-8") as f:
            for line in f:
                try:
                    done_ids.add(json.loads(line)["id"])
                except Exception:
                    pass
        print(f"Resume: {len(done_ids)} câu đã trả lời, skip chúng")

    mode = "a" if done_ids else "w"
    with open(out_path, mode, encoding="utf-8") as fout:
        for i, item in enumerate(questions):
            if item["id"] in done_ids:
                continue
            try:
                result = infer(item, split_root, rulebook)
            except Exception as e:
                result = {"id": item["id"], "type": "abstain", "answer": None, "_err": f"fatal:{str(e)[:150]}"}
            # Strip internal debug keys (giữ _code nếu --save-code)
            if args.save_code:
                submission_item = {k: v for k, v in result.items() if k != "_err"}
            else:
                submission_item = {k: v for k, v in result.items() if not k.startswith("_")}
            fout.write(json.dumps(submission_item, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, 'item') else str(o)) + "\n")
            fout.flush()  # flush ngay, không mất khi crash

            if result.get("type") == "abstain":
                n_abstain += 1
            else:
                n_answered += 1

            if (i + 1) % 50 == 0:
                print(f"  {i+1}/{len(questions)}  answered={n_answered}  abstain={n_abstain}", flush=True)

    print(f"\nDone → {out_path}  ({n_answered} answered, {n_abstain} abstain)")


if __name__ == "__main__":
    main()
