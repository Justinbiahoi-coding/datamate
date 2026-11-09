"""Phân loại các câu Gemini ĐÃ xử lý thành: correct / wrong / abstain.
+ Liệt kê các câu Gemini CHƯA xử lý (= to-do).
Xuất 3 file:
  - correct_ids.txt     (giữ nguyên, không cần redo)
  - problematic_ids.txt (wrong + abstain + chưa xử lý → cần Sonnet redo)
  - problematic_questions.jsonl  (full question items + gold + gemini verdict)
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from scorer import match_answer


def main():
    ROOT = Path(__file__).parent.parent
    sub_gemini = ROOT / "sub_gemini.jsonl"
    gold_path  = ROOT / "train" / "answers.jsonl"
    q_path     = ROOT / "train" / "questions.jsonl"

    with open(gold_path, encoding="utf-8") as f:
        gold = {json.loads(l)["id"]: json.loads(l) for l in f if l.strip()}
    with open(q_path, encoding="utf-8") as f:
        questions = {json.loads(l)["id"]: json.loads(l) for l in f if l.strip()}
    gemini = {}
    with open(sub_gemini, encoding="utf-8") as f:
        for line in f:
            it = json.loads(line)
            gemini[it["id"]] = it

    correct_ids = []
    problematic = []  # list of (qid, reason)

    for qid, gold_item in gold.items():
        gem = gemini.get(qid)
        if gem is None:
            problematic.append((qid, "not_processed"))
            continue

        if gem.get("type") == "abstain" or gem.get("answer") is None:
            problematic.append((qid, "abstain"))
            continue

        gold_ans = gold_item["answer"]
        if gold_ans is None:
            if gem.get("type") == "unanswerable":
                correct_ids.append(qid)
            else:
                problematic.append((qid, "wrong_unanswerable"))
            continue

        if match_answer(gem["type"], gem["answer"], gold_item["type"], gold_ans, gold_item.get("alias", [])):
            correct_ids.append(qid)
        else:
            problematic.append((qid, "wrong"))

    # Write outputs
    (ROOT / "correct_ids.txt").write_text("\n".join(correct_ids))
    (ROOT / "problematic_ids.txt").write_text("\n".join(p[0] for p in problematic))

    with open(ROOT / "problematic_questions.jsonl", "w", encoding="utf-8") as f:
        for qid, reason in problematic:
            if qid not in questions:
                continue
            item = dict(questions[qid])
            item["_reason"] = reason
            item["_gold_type"] = gold[qid]["type"]
            item["_gold_answer"] = gold[qid]["answer"]
            item["_gold_alias"] = gold[qid].get("alias", [])
            # Nếu Gemini đã thử → thêm Gemini's wrong answer để Sonnet biết what to avoid
            if qid in gemini:
                g = gemini[qid]
                item["_gemini_type"] = g.get("type")
                item["_gemini_answer"] = g.get("answer")
                item["_gemini_code"] = g.get("_code")
            f.write(json.dumps(item, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, 'item') else str(o)) + "\n")

    # Stats
    reasons = {}
    type_breakdown = {}
    for qid, reason in problematic:
        reasons[reason] = reasons.get(reason, 0) + 1
        gt = gold[qid]["type"] if gold[qid]["answer"] is not None else "unanswerable"
        type_breakdown.setdefault(gt, {}).setdefault(reason, 0)
        type_breakdown[gt][reason] += 1

    print(f"\n{'='*60}")
    print(f"Classification")
    print(f"{'='*60}")
    print(f"  ✓ Gemini correct:    {len(correct_ids)}")
    print(f"  ✗ Problematic:       {len(problematic)}")
    for reason, n in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"      {reason:<20} {n}")

    print(f"\n{'─'*60}")
    print(f"Problematic by GOLD type")
    print(f"{'─'*60}")
    print(f"{'type':<14} {'total':>6} {'wrong':>6} {'abstain':>8} {'not_processed':>15}")
    for gt in sorted(type_breakdown):
        d = type_breakdown[gt]
        tot = sum(d.values())
        print(f"{gt:<14} {tot:>6} {d.get('wrong',0):>6} {d.get('abstain',0):>8} {d.get('not_processed',0):>15}")

    print(f"\n→ problematic_ids.txt      ({len(problematic)} IDs)")
    print(f"→ correct_ids.txt           ({len(correct_ids)} IDs)")
    print(f"→ problematic_questions.jsonl ({len(problematic)} questions with context)")


if __name__ == "__main__":
    main()
