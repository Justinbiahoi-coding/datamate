"""Make the 31 base solutions with absolute /Users paths self-contained.

These rows in `sub_final2.jsonl` load data with
    sys.path.insert(0, '/Users/.../code'); from loader import load_business
    b = load_business(Path('/Users/.../train/data/biz_xxx'))
They are not in `audit_dependent.json` (that list only tracks /tmp helpers), but they
violate the same self-contained rules. This script replaces the loader call with the
sandbox `data` variable, removes the absolute-path imports, executes each row, and
compares the result with the stored `answer`.

Usage: python3 sub_selfcontained/fix_base_absolute.py [--limit N]
Writes: sub_selfcontained/base_fix.jsonl, sub_selfcontained/base_ids.json
"""
import argparse, copy, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
from agent import exec_code, infer_type  # noqa: E402
from loader import load_business  # noqa: E402
from verify_selfcontained import FORBIDDEN, same_value  # noqa: E402

OUT = ROOT / "sub_selfcontained"


def load_rows():
    rows = {}
    for line in open(ROOT / "sub_final2.jsonl"):
        r = json.loads(line)
        rows[r["id"]] = r
    for f in sorted((ROOT / "sub_haiku").glob("retry9_*.jsonl")):
        for line in open(f):
            r = json.loads(line)
            rows[r["id"]] = r
    return rows


def convert(code):
    out = []
    for line in code.splitlines():
        s = line.strip()
        if re.match(r"^\w+\.path\.insert\(", s):
            continue
        if re.match(r"^from\s+pathlib\s+import\s+Path\s*$", s):
            continue
        if re.match(r"^from\s+loader\s+import\s+load_business\s*$", s):
            continue
        m = re.match(r"^(\s*\w+\s*=\s*)load_business\(.*\)\s*$", line)
        if m:
            out.append(m.group(1) + "data")
            continue
        out.append(line)
    code = "\n".join(out)
    if not re.search(r"\bsys\.", code):
        code = re.sub(r"^import\s+sys\s*,\s*", "import ", code, flags=re.M)
        code = re.sub(r"^import\s+sys\s*\n", "", code, flags=re.M)
    if not re.search(r"\bPath\s*\(", code):
        code = re.sub(r"^from\s+pathlib\s+import\s+Path\s*\n", "", code, flags=re.M)
    return code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    rows = load_rows()
    qs = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "train/questions.jsonl")}
    dep = set(json.load(open(ROOT / "audit_dependent.json"))["dependent"])
    ids = [q for q, r in rows.items()
           if "_code" in r and re.search(r"/Users/", r["_code"]) and q not in dep]
    if a.limit:
        ids = ids[: a.limit]
    fixed, bad = [], []
    for qid in ids:
        r = rows[qid]
        biz = qs[qid]["business_id"]
        try:
            code = convert(r["_code"])
            why = [name for pat, name in FORBIDDEN if re.search(pat, code, re.M)]
            if why:
                raise RuntimeError("static: " + ",".join(why))
            data = copy.deepcopy(load_business(ROOT / "train" / "data" / biz))
            pt, pv = infer_type(exec_code(code, data, qs[qid]["as_of_date"]))
            if not same_value(pv, pt, r["answer"], r["type"]):
                raise RuntimeError(f"answer mismatch: stored={r['answer']!r} got={pv!r}")
            out = dict(r)
            out["_code"] = code
            out["_verdict"] = "correct"
            fixed.append(out)
        except Exception as e:
            bad.append({"id": qid, "error": repr(e)[:300]})
            print("FAIL", qid, biz, repr(e)[:160], flush=True)
    with open(OUT / "base_fix.jsonl", "w") as f:
        for r in fixed:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    json.dump([r["id"] for r in fixed], open(OUT / "base_ids.json", "w"))
    json.dump(bad, open(OUT / "base_unfixed.json", "w"), ensure_ascii=False, indent=1)
    print("DONE ok", len(fixed), "bad", len(bad))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
