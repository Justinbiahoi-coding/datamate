"""Run one solution against real data, grade vs gold (gold not revealed), save if correct.

python3 code/haiku_check.py BATCH_FILE QID CODE_FILE
Writes correct rows to sub_haiku/<batch name>.jsonl (one file per batch, no races).
"""
import sys, json
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "code"))
from agent import exec_code, infer_type  # noqa: E402
from loader import load_business  # noqa: E402
from scorer import match_answer  # noqa: E402

batch, qid, code_file = sys.argv[1:4]
q = next(json.loads(l) for l in open(batch) if json.loads(l)["id"] == qid)
code = Path(code_file).read_text()
biz = load_business(ROOT / "train" / "data" / q["business_id"])
try:
    res = exec_code(code, biz, q["as_of_date"])
except Exception as e:
    print(f"ERROR {type(e).__name__}: {str(e)[:400]}")
    sys.exit(1)
t, v = infer_type(res)
ga = q["_gold_answer"]
if ga is None:
    ok = t == "unanswerable"
elif isinstance(ga, (int, float)) and not isinstance(ga, bool):
    # real scoring is exact (rulebook §9): money to the dong, counts exact, percent to 2 decimals
    try:
        ok = abs(float(v) - float(ga)) <= 1e-6 * max(1.0, abs(float(ga)))
    except Exception:
        ok = False
else:
    ok = match_answer(t, v, q["_gold_type"], ga, q.get("_gold_alias", []))
print(f"got type={t} value={str(v)[:200]} | gold_type={q['_gold_type']} | {'CORRECT' if ok else 'WRONG'}")
if ok:
    out = ROOT / "sub_haiku" / (Path(batch).stem + ".jsonl")
    out.parent.mkdir(exist_ok=True)
    row = dict(id=qid, type=t, answer=v, _code=code, _verdict="correct", _attempts=1)
    with open(out, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
