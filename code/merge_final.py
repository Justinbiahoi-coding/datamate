"""Merge sub_gemini.jsonl + sub_sonnet.jsonl → sub_final.jsonl.

Logic per qid:
  - Nếu Sonnet correct (match gold) → dùng Sonnet (ưu tiên cao vì chất lượng cao hơn)
  - Elif Gemini correct → dùng Gemini
  - Else abstain

Ghi sub_final.jsonl full 3000 câu format submission + _code cho câu có correct.
Rồi dùng cho make_sft.py --from-submission.
"""
import json, sys, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scorer import match_answer


def is_correct(sub_item, gold_item):
    if sub_item is None or sub_item.get("answer") is None:
        return False
    if gold_item["answer"] is None:
        return sub_item.get("type") == "unanswerable"
    return match_answer(
        sub_item.get("type", ""), sub_item.get("answer"),
        gold_item["type"], gold_item["answer"],
        gold_item.get("alias", []),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gemini", default="sub_gemini.jsonl")
    parser.add_argument("--sonnet", default="sub_sonnet.jsonl")
    parser.add_argument("--gold", default="train/answers.jsonl")
    parser.add_argument("--out", default="sub_final.jsonl")
    args = parser.parse_args()

    with open(args.gold, encoding="utf-8") as f:
        gold = {json.loads(l)["id"]: json.loads(l) for l in f if l.strip()}

    gemini = {}
    if Path(args.gemini).exists():
        with open(args.gemini, encoding="utf-8") as f:
            for line in f:
                it = json.loads(line)
                gemini[it["id"]] = it

    sonnet = {}
    if Path(args.sonnet).exists():
        with open(args.sonnet, encoding="utf-8") as f:
            for line in f:
                it = json.loads(line)
                sonnet[it["id"]] = it

    n_sonnet = n_gemini = n_abstain = 0
    per_type = {}  # gold_type → {sonnet, gemini, abstain}

    with open(args.out, "w", encoding="utf-8") as fout:
        for qid, gold_item in gold.items():
            gt = gold_item["type"] if gold_item["answer"] is not None else "unanswerable"
            per_type.setdefault(gt, {"sonnet": 0, "gemini": 0, "abstain": 0})

            s_item = sonnet.get(qid)
            g_item = gemini.get(qid)

            if is_correct(s_item, gold_item):
                out = {k: v for k, v in s_item.items() if not k.startswith("_") or k == "_code"}
                out["_source"] = "sonnet"
                n_sonnet += 1
                per_type[gt]["sonnet"] += 1
            elif is_correct(g_item, gold_item):
                out = {k: v for k, v in g_item.items() if not k.startswith("_") or k == "_code"}
                out["_source"] = "gemini"
                n_gemini += 1
                per_type[gt]["gemini"] += 1
            else:
                out = {"id": qid, "type": "abstain", "answer": None, "_source": "none"}
                n_abstain += 1
                per_type[gt]["abstain"] += 1

            fout.write(json.dumps(out, ensure_ascii=False,
                                  default=lambda o: o.item() if hasattr(o, 'item') else str(o)) + "\n")

    total = n_sonnet + n_gemini + n_abstain
    print(f"\n{'='*60}")
    print(f"FINAL MERGE → {args.out}")
    print(f"{'='*60}")
    print(f"  Total:    {total}")
    print(f"  Sonnet:   {n_sonnet:>5}  ({n_sonnet/total*100:.1f}%)")
    print(f"  Gemini:   {n_gemini:>5}  ({n_gemini/total*100:.1f}%)")
    print(f"  Abstain:  {n_abstain:>5}  ({n_abstain/total*100:.1f}%)")
    print(f"  Covered:  {n_sonnet + n_gemini}  ({(n_sonnet+n_gemini)/total*100:.1f}%)")

    print(f"\n{'─'*60}")
    print(f"PER-TYPE SOURCE")
    print(f"{'─'*60}")
    print(f"{'type':<14} {'total':>6} {'sonnet':>7} {'gemini':>7} {'abstain':>8}")
    for t in sorted(per_type):
        c = per_type[t]
        tot = sum(c.values())
        print(f"{t:<14} {tot:>6} {c['sonnet']:>7} {c['gemini']:>7} {c['abstain']:>8}")


if __name__ == "__main__":
    main()
