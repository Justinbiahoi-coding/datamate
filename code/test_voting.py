"""Offline check of the voting/abstain/repair logic in inference.solve_batch (no GPU: fake generator).

python3 code/test_voting.py
"""
import json, multiprocessing as mp, os, sys, warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).parent.parent
os.chdir(ROOT)
sys.path.insert(0, "code")
os.environ.update(VOTE_K="5", VOTE_MIN_AGREE="2", VOTE_MIN_SHARE="0.4", VOTE_REPAIRS="2")
import inference  # noqa: E402

qs = {json.loads(l)["id"]: json.loads(l) for l in open("train/questions.jsonl")}
gold = {json.loads(l)["id"]: json.loads(l) for l in open("train/answers.jsonl")}
codes = {json.loads(l)["id"]: json.loads(l)["_code"] for l in open("sub_final6.jsonl")}
ids = [i for i in json.load(open("holdout_ids.json")) if gold[i]["answer"] is not None][:10]

WA, WB, ERR = "RESULT = 123456789", "RESULT = 987", "RESULT = no_such_table['x'].sum()"
# scenario -> (first-round candidates [greedy + 4 sampled], repair output, expected outcome)
SCEN = [
    (["OK", "OK", WA, ERR, ERR], ERR, "correct"),     # majority right
    ([WA, WB, ERR, ERR, ERR], "OK", "correct"),       # repair with real columns fixes two failures
    ([ERR] * 5, ERR, "abstain"),                      # nothing runs
    ([WA, WA, "OK", ERR, ERR], ERR, "wrong"),         # confident but wrong: voting cannot save it
    (["OK", WA, ERR, ERR, ERR], ERR, "abstain"),      # 1-1 tie
]
plan = {qid: SCEN[n % len(SCEN)] for n, qid in enumerate(ids)}
by_question = {qs[i]["question"]: i for i in ids}


def fake_gen(msg_lists, n, temperature):
    out = []
    for m in msg_lists:
        qid = next(v for q, v in by_question.items() if q in m[1]["content"])
        first, repair, _ = plan[qid]
        if len(m) > 2:
            picks = [repair]
        else:
            picks = first[:1] if temperature == 0 else first[1:1 + n]
        out.append([f"```python\n{codes[qid] if p == 'OK' else p}\n```" for p in picks])
    return out


if __name__ == "__main__":
    pool = mp.get_context("fork").Pool(4)
    res = inference.solve_batch([qs[i] for i in ids], fake_gen, pool, ROOT / "train",
                                (ROOT / "train/rulebook.md").read_text(encoding="utf-8"))
    pool.close()
    from apply_overlay import strict
    bad = 0
    for qid in ids:
        r = res[qid]
        got = "abstain" if r["type"] == "abstain" else ("correct" if strict(r["type"], r["answer"], gold[qid]) else "wrong")
        exp = plan[qid][2]
        bad += got != exp
        print(f"{qid} expected={exp:8s} got={got:8s} votes={r.get('_votes', {}).get('votes')}")
    assert bad == 0, f"{bad} scenario(s) behaved unexpectedly"
    print("voting logic OK")
