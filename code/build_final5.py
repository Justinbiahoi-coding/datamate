import json, glob, sys, copy, warnings, datetime as dt, os
from pathlib import Path
from collections import Counter
os.chdir("/Users/buivanthien/Learn/zalo chelen/datamate")
warnings.filterwarnings("ignore"); sys.path.insert(0, "code")
from agent import exec_code, infer_type
from loader import load_business
import datefix

qs = {json.loads(l)["id"]: json.loads(l) for l in open("train/questions.jsonl")}
final = {}
for l in open("sub_final4.jsonl"):
    r = json.loads(l)
    if r.get("_code") and r.get("type") != "abstain": final[r["id"]] = r

def load(pat):
    d = {}
    for f in sorted(glob.glob(pat)):
        for l in open(f): r = json.loads(l); d[r["id"]] = r
    return d

ok = json.load(open("overlay_ok.json"))
r11, r12 = load("sub_haiku/retry11_*.jsonl"), load("sub_haiku/retry12_*.jsonl")
for tag, d, ids in (("resolve11", r11, ok["r11"]), ("compact12", r12, ok["r12"])):
    for i in ids:
        r = d[i]
        final[i] = {"id": i, "type": r["type"], "answer": r["answer"], "_code": r["_code"], "_source": tag}
print("sau overlay:", len(final), Counter(r.get("_source") for r in final.values()).most_common(4), flush=True)

base, n_fix, n_err, n_diff = {}, 0, 0, 0
for i, r in final.items():
    q = qs[i]
    new = datefix.transform(r["_code"], q["as_of_date"], q["question"])
    if new is None: continue
    b = q["business_id"]
    if b not in base: base[b] = load_business(Path("train/data") / b)
    try:
        pt, pv = infer_type(exec_code(new, copy.deepcopy(base[b]), q["as_of_date"]))
        if not ((str(pv) == str(r["answer"])) or (pt == r["type"] and pv == r["answer"])): n_diff += 1; continue
        for k in (3, 40):
            exec_code(new, copy.deepcopy(base[b]), (dt.date.fromisoformat(q["as_of_date"]) + dt.timedelta(days=k)).isoformat())
        r["_code"] = new; r["_source"] = str(r.get("_source", "")) + "+datefix"; n_fix += 1
    except Exception:
        n_err += 1
print("datefix áp dụng:", n_fix, "| khác kết quả:", n_diff, "| lỗi khi thử ngày khác:", n_err, flush=True)
with open("sub_final5.jsonl", "w") as f:
    for i in qs:
        if i in final: f.write(json.dumps(final[i], ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
print("DONE", len(final))
