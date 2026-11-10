"""Batches for the code-canonicalization pass (see CANON_CODE_GUIDE.md).

python3 code/make_batches_canon.py [--src sub_final6.jsonl]
  batches_canon/canon_XXX.jsonl : training solutions that define helper functions or exceed 1200 chars, 20 per batch.
Hold-out ids are skipped (never used for training). Rows carry _gold_* only so haiku_check.py can grade.
"""
import argparse, json, os, re
from pathlib import Path

os.chdir(Path(__file__).parent.parent)
ap = argparse.ArgumentParser()
ap.add_argument("--src", default="sub_final6.jsonl")
a = ap.parse_args()

qs = {json.loads(l)["id"]: json.loads(l) for l in open("train/questions.jsonl")}
gold = {json.loads(l)["id"]: json.loads(l) for l in open("train/answers.jsonl")}
rows = {json.loads(l)["id"]: json.loads(l) for l in open(a.src)}
holdout = set(json.load(open("holdout_ids.json")))

need = [i for i, r in rows.items()
        if i not in holdout and (re.search(r"^\s*def \w+", r["_code"], re.M) or len(r["_code"]) > 1200)]
need.sort(key=lambda i: -len(rows[i]["_code"]))

Path("batches_canon").mkdir(exist_ok=True)
for k in range(0, len(need), 20):
    with open(f"batches_canon/canon_{k // 20:03d}.jsonl", "w") as f:
        for i in need[k:k + 20]:
            q, g = qs[i], gold[i]
            f.write(json.dumps(dict(id=i, business_id=q["business_id"], question=q["question"],
                                    as_of_date=q["as_of_date"], _gold_type=g["type"], _gold_answer=g["answer"],
                                    _gold_alias=g.get("alias", []), _old_code=rows[i]["_code"]),
                               ensure_ascii=False) + "\n")
print(f"batches_canon: {len(need)} questions, {(len(need) + 19) // 20} batches")
