"""Create agent batches for the two optional improvements, from the current sub_final5.jsonl.

python3 code/make_batches_next.py
  batches_compact/compact_XXX.jsonl : codes longer than 3000 chars (rewrite compactly), 20 per batch, with _old_code
  batches_dates/dates_XXX.jsonl     : questions with relative-time words whose code never uses as_of_date (rewrite to use it), 20 per batch
Rows carry _gold_* fields only so code/haiku_check.py can grade; agents must not read them.
"""
import json, re, os, unicodedata
from pathlib import Path
os.chdir(Path(__file__).parent.parent)
na = lambda s: unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()
qs = {json.loads(l)["id"]: json.loads(l) for l in open("train/questions.jsonl")}
gold = {json.loads(l)["id"]: json.loads(l) for l in open("train/answers.jsonl")}
rows = {json.loads(l)["id"]: json.loads(l) for l in open("sub_final5.jsonl")}
REL = re.compile(r"hom nay|hom qua|bua qua|tuan nay|tuan truoc|tuan roi|thang nay|thang truoc|thang roi|nam nay|dau nam|gan nhat|den het|toi nay|quy nay|quy truoc|tinh den")

def item(i):
    q, g = qs[i], gold[i]
    return dict(id=i, business_id=q["business_id"], question=q["question"], as_of_date=q["as_of_date"],
                _gold_type=g["type"], _gold_answer=g["answer"], _gold_alias=g.get("alias", []), _old_code=rows[i]["_code"])

def write(ids, d, prefix, size=20):
    Path(d).mkdir(exist_ok=True)
    for k in range(0, len(ids), size):
        with open(f"{d}/{prefix}_{k // size:03d}.jsonl", "w") as f:
            for i in ids[k:k + size]: f.write(json.dumps(item(i), ensure_ascii=False) + "\n")
    print(d, len(ids), "câu,", (len(ids) + size - 1) // size, "batch")

long_ids = sorted((i for i in rows if len(rows[i]["_code"]) > 3000), key=lambda i: -len(rows[i]["_code"]))
date_ids = [i for i in rows if REL.search(na(qs[i]["question"])) and "as_of_date" not in rows[i]["_code"]]
write(long_ids, "batches_compact", "compact")
write(date_ids, "batches_dates", "dates")
