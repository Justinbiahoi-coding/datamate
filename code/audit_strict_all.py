"""Strict full audit: re-runs every _code in sub_final5.jsonl on real data (fresh deep-copied data per question), exact match vs gold.
Run from the datamate folder: python3 code/audit_strict_all.py  (about 17 minutes). Writes audit_v5_rerun.json."""
import json, glob, re, sys, os, copy, ast, time
from pathlib import Path
from collections import Counter, defaultdict
ROOT = Path("/Users/buivanthien/Learn/zalo chelen/datamate")
os.chdir(ROOT); sys.path.insert(0, "code")
import warnings; warnings.filterwarnings("ignore")
from agent import exec_code, infer_type
from loader import load_business
from scorer import match_answer

gold = {json.loads(l)["id"]: json.loads(l) for l in open("train/answers.jsonl")}
qs = {json.loads(l)["id"]: json.loads(l) for l in open("train/questions.jsonl")}
rows = {}
for l in open("sub_final5.jsonl"):
    r = json.loads(l)
    if r.get("type") != "abstain" and r.get("_code"):
        rows[r["id"]] = (r.get("_source", "?"), r)
dups = 0
print("rows:", len(rows), "dup-skipped:", dups, "missing from gold:", len(set(gold) - set(rows)), flush=True)

def gtype(g): return g["type"] if g["answer"] is not None else "unanswerable"
def strict(pt, pv, g):
    ga = g["answer"]
    if ga is None: return pt == "unanswerable"
    if isinstance(ga, bool) or isinstance(pv, bool): return pv == ga
    if isinstance(ga, (int, float)):
        try: return abs(float(pv) - float(ga)) <= 1e-6 * max(1.0, abs(float(ga)))
        except Exception: return False
    return pv == ga

base = {}
out = []
t0 = time.time()
for n, (qid, (src, r)) in enumerate(rows.items(), 1):
    q = qs[qid]; g = gold[qid]; b = q["business_id"]; code = r["_code"]
    if b not in base: base[b] = load_business(ROOT / "train" / "data" / b)
    rec = dict(id=qid, src=src, biz=b, gt=gtype(g), status="ok", syntax=True, clen=len(code))
    try: ast.parse(code)
    except SyntaxError: rec["syntax"] = False
    rec["has_result"] = bool(re.search(r"\bRESULT\s*=", code))
    rec["wallclock"] = bool(re.search(r"datetime\.(now|today)|date\.today|Timestamp\.(now|today)", code))
    try:
        data = copy.deepcopy(base[b])
        pt, pv = infer_type(exec_code(code, data, q["as_of_date"]))
        rec["lenient"] = bool(match_answer(pt, pv, gtype(g), g["answer"], g.get("alias", [])))
        rec["strict"] = bool(strict(pt, pv, g))
        if not rec["lenient"]: rec["status"] = "wrong"
        elif not rec["strict"]: rec["status"] = "tolerance_only"
        if rec["lenient"] and not rec["strict"]:
            try: rec["rel"] = abs(float(pv) - float(g["answer"])) / max(abs(float(g["answer"])), 1e-9)
            except Exception: rec["rel"] = None
    except Exception as e:
        rec["status"] = "exec_error"; rec["err"] = f"{type(e).__name__}: {str(e)[:90]}"
    # hardcode check
    ga = g["answer"]; c = code.replace(",", "").replace("_", ""); vals = set()
    if isinstance(ga, (int, float)) and not isinstance(ga, bool):
        vals = {str(int(ga)) if float(ga).is_integer() else str(ga), f"{ga:g}"}
    elif isinstance(ga, str) and len(ga) >= 3: vals = {ga}
    rec["hardcode_suspect"] = any(len(v) >= 3 and re.search(r"(?<![\d.])" + re.escape(v) + r"(?![\d])", c) for v in vals)
    out.append(rec)
    if n % 500 == 0: print(n, "done", round(time.time() - t0), "s", flush=True)
json.dump(out, open("audit_v5_rerun.json", "w"), ensure_ascii=False)
print("DONE", len(out), round(time.time() - t0), "s")
