"""Progress of the canonicalization pass (see CANON_CODE_GUIDE.md). Static checks only, no code is executed.

python3 code/canon_status.py              # summary
python3 code/canon_status.py --next 10    # next 10 batches that still have pending ids, with the ids to do

A question counts as DONE when sub_haiku/canon_*.jsonl holds a saved row for it that also passes the static rules
(no `def`, <= 1500 chars, shorter than the old code, still uses as_of_date if the old code did, no forbidden construct).
The real acceptance test is apply_overlay.py (it re-executes the code); this script only says what is left to do.
"""
import argparse, glob, json, os, re
from pathlib import Path

os.chdir(Path(__file__).parent.parent)
FORB = [r"sys\.path", r"load_business", r"/tmp", r"/Users/", r"train/data", r"\bopen\(",
        r"^\s*(import|from)\s+(h\d*|loader|selfgen|adapters|_h)\b", r"\b(cancellation_rate|find_revenue_col)\s*\("]

ap = argparse.ArgumentParser()
ap.add_argument("--next", type=int, default=0)
a = ap.parse_args()

old = {}
order = []
for f in sorted(glob.glob("batches_canon/canon_*.jsonl")):
    n = Path(f).stem.split("_")[1]
    for l in open(f):
        r = json.loads(l)
        old[r["id"]] = r["_old_code"]
        order.append((n, r["id"]))

saved = {}
for f in sorted(glob.glob("sub_haiku/canon_*.jsonl")):
    for l in open(f):
        r = json.loads(l)
        saved[r["id"]] = r["_code"]  # last row wins, like apply_overlay


def acceptable(i):
    c = saved.get(i)
    if c is None or i not in old:
        return False
    o = old[i]
    if re.search(r"^\s*def \w+", c, re.M) or len(c) > 1500 or len(c) >= len(o):
        return False
    if "as_of_date" in o and "as_of_date" not in c:
        return False
    return not any(re.search(p, c, re.M) for p in FORB)


done = {i for _, i in order if acceptable(i)}
pending = {}
for n, i in order:
    if i not in done:
        pending.setdefault(n, []).append(i)
saved_bad = [i for i in saved if i in old and i not in done]
batches = sorted({n for n, _ in order})
print(f"questions {len(order)} | done {len(done)} | pending {len(order) - len(done)} "
      f"(of which saved but not acceptable: {len(saved_bad)})")
print(f"batches {len(batches)} | fully done {len(batches) - len(pending)} | with pending ids {len(pending)}")
if a.next:
    print()
    for n in sorted(pending)[:a.next]:
        print(f"{n} pending={len(pending[n])}/20 ids={','.join(pending[n])}")
