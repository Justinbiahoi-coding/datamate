"""Verify new agent solutions and overlay them on the current code table.

python3 code/apply_overlay.py --prefix compact --require-shorter --src sub_final5.jsonl --out sub_final6.jsonl
python3 code/apply_overlay.py --prefix dates   --require-asof    --src sub_final6.jsonl --out sub_final7.jsonl

Reads sub_haiku/<prefix>_*.jsonl (last row per id wins). A row replaces the existing one only if it
- has no forbidden construct (sys.path, load_business, helper imports, /tmp, /Users, train/data, open(, cancellation_rate(, find_revenue_col()),
- runs on fresh deep-copied data and matches the gold EXACTLY (numbers/percent exact; strings/lists via scorer with aliases),
- (--require-shorter) is shorter than the code it replaces, (--require-asof) uses as_of_date.
Rejected ids are listed in <out>.rejected.json. Afterwards rebuild the training set:
python3 code/make_sft.py --from-submission <out> --out sft_data_vN.jsonl --max-chars 45000 --no-dedup --prompt-version v2
"""
import argparse, copy, glob, json, os, re, sys, warnings
from pathlib import Path

ROOT = Path(__file__).parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "code"))
warnings.filterwarnings("ignore")
from agent import exec_code, infer_type  # noqa: E402
from loader import load_business  # noqa: E402
from scorer import match_answer  # noqa: E402

FORB = [r"sys\.path", r"load_business", r"/tmp", r"/Users/", r"train/data", r"\bopen\(",
        r"^\s*(import|from)\s+(h\d*|loader|selfgen|adapters|_h)\b", r"\b(cancellation_rate|find_revenue_col)\s*\("]


def strict(pt, pv, g):
    ga = g["answer"]
    if ga is None:
        return pt == "unanswerable"
    if isinstance(ga, bool) or isinstance(pv, bool):
        return pv == ga
    if isinstance(ga, (int, float)):
        try:
            return abs(float(pv) - float(ga)) <= 1e-6 * max(1.0, abs(float(ga)))
        except Exception:
            return False
    return match_answer(pt, pv, g["type"], ga, g.get("alias", []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--src", default="sub_final5.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--require-shorter", action="store_true")
    ap.add_argument("--require-asof", action="store_true")
    ap.add_argument("--forbid-def", action="store_true", help="reject code that defines its own functions")
    ap.add_argument("--max-chars", type=int, default=0, help="reject code longer than this (0 = no limit)")
    ap.add_argument("--keep-asof", action="store_true", help="reject if the old code used as_of_date and the new one does not")
    a = ap.parse_args()
    gold = {json.loads(l)["id"]: json.loads(l) for l in open("train/answers.jsonl")}
    qs = {json.loads(l)["id"]: json.loads(l) for l in open("train/questions.jsonl")}
    table = {}
    for l in open(a.src):
        r = json.loads(l)
        table[r["id"]] = r
    new = {}
    for f in sorted(glob.glob(f"sub_haiku/{a.prefix}_*.jsonl")):
        for l in open(f):
            r = json.loads(l)
            new[r["id"]] = r
    base, rejected, applied = {}, {}, 0
    for i, r in new.items():
        if i not in table:
            rejected[i] = "id not in source table"; continue
        c, q = r["_code"], qs[i]
        if any(re.search(p, c, re.M) for p in FORB):
            rejected[i] = "forbidden construct"; continue
        if a.require_shorter and len(c) >= len(table[i]["_code"]):
            rejected[i] = "not shorter"; continue
        if a.require_asof and "as_of_date" not in c:
            rejected[i] = "does not use as_of_date"; continue
        if a.keep_asof and "as_of_date" in table[i]["_code"] and "as_of_date" not in c:
            rejected[i] = "dropped as_of_date"; continue
        if a.forbid_def and re.search(r"^\s*def \w+", c, re.M):
            rejected[i] = "defines a function"; continue
        if a.max_chars and len(c) > a.max_chars:
            rejected[i] = f"longer than {a.max_chars} chars"; continue
        b = q["business_id"]
        if b not in base:
            base[b] = load_business(ROOT / "train" / "data" / b)
        try:
            pt, pv = infer_type(exec_code(c, copy.deepcopy(base[b]), q["as_of_date"]))
        except Exception as e:
            rejected[i] = "exec error: " + str(e)[:60]; continue
        if not strict(pt, pv, gold[i]):
            rejected[i] = f"not exact: got {str(pv)[:30]}"; continue
        table[i] = {"id": i, "type": pt, "answer": pv, "_code": c, "_source": a.prefix}
        applied += 1
    with open(a.out, "w") as f:
        for i in qs:
            if i in table:
                f.write(json.dumps(table[i], ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
    json.dump(rejected, open(a.out + ".rejected.json", "w"), ensure_ascii=False, indent=1)
    print(f"candidates {len(new)} | applied {applied} | rejected {len(rejected)} -> {a.out}")


if __name__ == "__main__":
    main()
