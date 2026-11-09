"""Merge nhiều submission files → 1 file "high-confidence" (technique #1: majority voting).

Logic:
  Với mỗi câu, lấy answer từ tất cả submissions.
  - Nếu ≥2 submissions AGREE (match_answer) → chọn answer đó + giữ code từ sub đó.
  - Nếu chỉ 1 submission trả lời → optionally keep hoặc skip (--min-agree).
  - Nếu tất cả abstain → abstain.

Dùng cho SFT: merge sub_gemini.jsonl + sub_qwen14b.jsonl → sub_consensus.jsonl,
rồi make_sft.py --from-submission sub_consensus.jsonl.

Usage:
  python merge_submissions.py \
    --inputs sub_gemini.jsonl sub_qwen14b.jsonl \
    --out sub_consensus.jsonl \
    --min-agree 2
"""
import json, argparse
from pathlib import Path
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).parent))
from scorer import match_answer


def answers_agree(a: dict, b: dict) -> bool:
    """Hai submission items có match answer nhau không (symmetric match_answer)."""
    if a.get("answer") is None or b.get("answer") is None:
        return a.get("answer") is None and b.get("answer") is None
    return match_answer(
        a.get("type", ""), a.get("answer"),
        b.get("type", ""), b.get("answer"),
        [],
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True,
                        help="Các submission.jsonl files để merge")
    parser.add_argument("--out", default="sub_consensus.jsonl")
    parser.add_argument("--min-agree", type=int, default=2,
                        help="Số sub tối thiểu phải agree (default 2)")
    args = parser.parse_args()

    # Load all subs: qid → list of items (one per source)
    all_subs = defaultdict(list)
    for src in args.inputs:
        with open(src, encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                item["_src"] = Path(src).name
                all_subs[item["id"]].append(item)

    n_consensus = n_single = n_disagree = n_abstain = 0
    with open(args.out, "w", encoding="utf-8") as fout:
        for qid, items in all_subs.items():
            # Only non-abstain items
            answered = [x for x in items if x.get("answer") is not None
                        and x.get("type") not in ("abstain", "")]

            if not answered:
                # All abstain
                fout.write(json.dumps({"id": qid, "type": "abstain", "answer": None},
                                      ensure_ascii=False) + "\n")
                n_abstain += 1
                continue

            # Group by equivalence class (match_answer)
            groups = []
            for a in answered:
                placed = False
                for g in groups:
                    if answers_agree(a, g[0]):
                        g.append(a)
                        placed = True
                        break
                if not placed:
                    groups.append([a])

            # Pick largest group
            groups.sort(key=len, reverse=True)
            best = groups[0]

            if len(best) >= args.min_agree:
                # Consensus
                winner = best[0]
                out = {
                    "id": qid,
                    "type": winner["type"],
                    "answer": winner["answer"],
                    "_code": winner.get("_code"),
                    "_src": "+".join(sorted(x["_src"] for x in best)),
                    "_n_agree": len(best),
                }
                n_consensus += 1
            elif len(answered) == 1 and args.min_agree == 1:
                # Chỉ 1 sub answered, min_agree=1 cho qua
                winner = answered[0]
                out = {
                    "id": qid,
                    "type": winner["type"],
                    "answer": winner["answer"],
                    "_code": winner.get("_code"),
                    "_src": winner["_src"],
                    "_n_agree": 1,
                }
                n_single += 1
            else:
                # Disagreement — abstain for safety
                fout.write(json.dumps({"id": qid, "type": "abstain", "answer": None},
                                      ensure_ascii=False) + "\n")
                n_disagree += 1
                continue

            fout.write(json.dumps(out, ensure_ascii=False,
                                  default=lambda o: o.item() if hasattr(o, 'item') else str(o)) + "\n")

    total = n_consensus + n_single + n_disagree + n_abstain
    print(f"\n{'='*60}")
    print(f"MERGED → {args.out}  ({total} questions)")
    print(f"{'='*60}")
    print(f"  consensus (≥{args.min_agree} agree):  {n_consensus}")
    print(f"  single-source answer:        {n_single}")
    print(f"  disagree (→ abstain):        {n_disagree}")
    print(f"  all-abstain:                 {n_abstain}")


if __name__ == "__main__":
    main()
