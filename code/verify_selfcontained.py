"""Verify solutions are self-contained and correct.

python3 code/verify_selfcontained.py FILE.jsonl [--ids ids.json] [--out report.json]

Static: forbidden patterns (sys.path, load_business, train/, /tmp, open(, import of helper modules).
Dynamic: exec with fresh deep-copied data, helper modules blocked, compare vs the row's stored
`answer` (the self-contained rewrite must preserve it). With --check-gold, also compare vs
`train/answers.jsonl`; that intentionally flags the known tolerance-only rows.
Exit code 0 only if every checked row passes.
"""
import sys, json, re, copy, ast, argparse, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "code"))
from agent import exec_code, infer_type  # noqa: E402
from loader import load_business  # noqa: E402

FORBIDDEN = [
    (r"sys\.path", "sys.path"), (r"load_business", "load_business"), (r"train/data|train\\data", "train/data path"),
    (r"/tmp|/Users/", "absolute path"), (r"\bopen\(", "open()"), (r"^\s*(import|from)\s+(h\d*|loader|selfgen|adapters|_h)\b", "helper import"),
    (r"^\s*import\s+\w+\s*,\s*h\d*\b", "helper import"), (r"\bimportlib\b|\bruntime\b|\bsubprocess\b|\bos\.system\b", "dynamic import/exec"),
]

def _num(x):
    if isinstance(x, bool): return None
    try: return float(str(x).rstrip("%").replace(",", ""))
    except Exception: return None


def _decimals(x):
    s = str(x).rstrip("%")
    return len(s.split(".")[1]) if "." in s else 0


def _round_half_up(x, d):
    from decimal import Decimal, ROUND_HALF_UP
    q = Decimal("1") if d == 0 else Decimal("1." + "0" * d)
    return float(Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP))


def same_value(pv, pt, av, at):
    """Compare a produced value with an expected answer, tolerating stored rounding."""
    if av is None or at == "unanswerable":
        return pt == "unanswerable"
    if at == "boolean":
        m = {"true": True, "false": False, "có": True, "không": False, "yes": True, "no": False}
        f = lambda v: m.get(str(v).strip().lower(), str(v).strip().lower())
        return f(pv) == f(av)
    if at in ("number", "percent"):
        p, g = _num(pv), _num(av)
        if p is None or g is None: return False
        d = _decimals(av)
        return abs(_round_half_up(p, d) - g) <= 1e-9 or abs(p - g) <= max(1e-9, 1e-7 * abs(g))
    if at == "list":
        if not (isinstance(pv, list) and isinstance(av, list)) or len(pv) != len(av): return False
        return all(str(x).strip().lower() == str(y).strip().lower() for x, y in zip(pv, av))
    if at == "table":
        def rows(x): return [x.get("columns", [])] + list(x.get("rows", [])) if isinstance(x, dict) else x
        pr, gr = rows(pv), rows(av)
        return pr == gr
    return str(pv).strip().lower() == str(av).strip().lower()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file"); ap.add_argument("--ids"); ap.add_argument("--out", default="verify_report.json")
    ap.add_argument("--check-gold", action="store_true",
                    help="also require a strict match vs train/answers.jsonl (flags known tolerance-only rows)")
    a = ap.parse_args()
    gold = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "train/answers.jsonl")}
    qs = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "train/questions.jsonl")}
    want = set(json.load(open(a.ids))) if a.ids else None
    rows = {}
    for l in open(a.file):
        r = json.loads(l)
        if want is None or r["id"] in want: rows[r["id"]] = r
    for name in ["h"] + [f"h{n}" for n in range(100, 131)]:
        sys.modules[name] = None
    base, bad, ok = {}, [], 0
    for qid, r in rows.items():
        code = r.get("_code", ""); why = []
        try: ast.parse(code)
        except SyntaxError as e: why.append(f"syntax: {e.msg}")
        for pat, name in FORBIDDEN:
            if re.search(pat, code, re.M): why.append(f"forbidden: {name}")
        if not re.search(r"\bRESULT\s*=", code): why.append("no RESULT")
        if not why:
            q = qs[qid]; b = q["business_id"]
            if b not in base: base[b] = load_business(ROOT / "train/data" / b)
            try:
                pt, pv = infer_type(exec_code(code, copy.deepcopy(base[b]), q["as_of_date"]))
                if not same_value(pv, pt, r.get("answer"), r.get("type")):
                    why.append(f"differs from stored answer: got {str(pv)[:60]} type {pt}")
                if a.check_gold:
                    g = gold[qid]
                    if not same_value(pv, pt, g["answer"], g["type"]):
                        why.append(f"gold mismatch/tolerance-only: got {str(pv)[:60]} type {pt}")
            except Exception as e:
                why.append(f"exec: {type(e).__name__}: {str(e)[:80]}")
        if why: bad.append({"id": qid, "why": why})
        else: ok += 1
    json.dump({"checked": len(rows), "ok": ok, "bad": bad}, open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"checked {len(rows)} | ok {ok} | bad {len(bad)} -> {a.out}")
    for b in bad[:10]: print("  ", b["id"], b["why"])
    sys.exit(0 if not bad else 1)

if __name__ == "__main__":
    main()
