"""Local scorer for DataMate submissions.

Scoring: +1 correct, -1 wrong, 0 abstain/missing.
Run: python scorer.py --split train --sub submission.jsonl
"""
import json
import argparse
import sys
from pathlib import Path

NUMBER_TOLERANCE = 1  # ±1 for rounding


def normalize_text(s: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFC", str(s).strip().lower())


def match_answer(pred_type, pred_ans, gold_type, gold_ans, alias) -> bool:
    if pred_type != gold_type:
        return False

    if gold_ans is None:
        return pred_ans is None or str(pred_ans).lower() in ("unanswerable", "none", "null")

    if gold_type == "number":
        try:
            return abs(float(pred_ans) - float(gold_ans)) <= NUMBER_TOLERANCE
        except (TypeError, ValueError):
            return False

    if gold_type == "percent":
        try:
            # Accept e.g. 2.08 or "2.08%" both
            p = float(str(pred_ans).rstrip("%"))
            g = float(str(gold_ans).rstrip("%"))
            # Use round() to avoid float precision trap: abs(1.21-1.20) = 0.010000...9 > 0.01
            return round(abs(p - g), 10) <= 0.01
        except (TypeError, ValueError):
            return False

    if gold_type == "boolean":
        mapping = {"true": True, "false": False, "có": True, "không": False, "yes": True, "no": False}
        p = str(pred_ans).strip().lower()
        g = str(gold_ans).strip().lower()
        pv = mapping.get(p, p)
        gv = mapping.get(g, g)
        return pv == gv

    if gold_type == "date":
        return normalize_text(pred_ans) == normalize_text(gold_ans)

    if gold_type == "string":
        pn = normalize_text(pred_ans)
        candidates = {normalize_text(gold_ans)} | {normalize_text(a) for a in (alias or [])}
        return pn in candidates

    if gold_type == "unanswerable":
        return str(pred_ans).lower() in ("unanswerable", "none", "null", "")

    if gold_type == "list":
        if not isinstance(pred_ans, list) or not isinstance(gold_ans, list):
            return False
        if len(pred_ans) != len(gold_ans):
            return False
        return all(normalize_text(p) == normalize_text(g) for p, g in zip(pred_ans, gold_ans))

    if gold_type == "table":
        # Gold may be dict {columns, rows} or list-of-lists
        def to_rows(t):
            if isinstance(t, dict):
                cols = t.get("columns", [])
                rows = t.get("rows", [])
                return [cols] + rows
            return t  # already list-of-lists

        pred_rows = to_rows(pred_ans)
        gold_rows = to_rows(gold_ans)
        if not isinstance(pred_rows, list) or not isinstance(gold_rows, list):
            return False
        if len(pred_rows) != len(gold_rows):
            return False
        return all(
            isinstance(pr, list) and isinstance(gr, list) and
            len(pr) == len(gr) and
            all(normalize_text(pc) == normalize_text(gc) for pc, gc in zip(pr, gr))
            for pr, gr in zip(pred_rows, gold_rows)
        )

    return normalize_text(pred_ans) == normalize_text(gold_ans)


def score(split_root: Path, sub_path: Path, verbose: bool = False):
    gold_index = {}
    with open(split_root / "answers.jsonl", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            gold_index[item["id"]] = item

    sub_index = {}
    with open(sub_path, encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            sub_index[item["id"]] = item

    correct = wrong = abstain = missing = 0
    details = []

    for qid, gold in gold_index.items():
        pred = sub_index.get(qid)

        if pred is None:
            # ponytail: missing counts as abstain (0 points)
            abstain += 1
            details.append((qid, "missing", 0))
            continue

        pred_type = pred.get("type", "")
        pred_ans = pred.get("answer")

        if pred_type == "abstain" or pred_ans is None:
            abstain += 1
            details.append((qid, "abstain", 0))
            continue

        gold_type = gold["type"]
        gold_ans = gold["answer"]
        alias = gold.get("alias", [])

        if gold_ans is None:
            # True answer is unanswerable
            if pred_type == "unanswerable":
                correct += 1
                details.append((qid, "correct", 1))
            else:
                wrong += 1
                details.append((qid, "wrong", -1))
        elif match_answer(pred_type, pred_ans, gold_type, gold_ans, alias):
            correct += 1
            details.append((qid, "correct", 1))
        else:
            wrong += 1
            details.append((qid, "wrong", -1))

    total = correct + wrong + abstain
    score_val = correct - wrong
    max_score = total  # if all correct

    print(f"Questions: {total}  |  Correct: {correct}  Wrong: {wrong}  Abstain/Missing: {abstain}")
    print(f"Score: {score_val}/{max_score}  ({score_val/max_score*100:.1f}%)")
    print(f"Accuracy (answered): {correct/(correct+wrong)*100:.1f}%" if (correct + wrong) else "No answered questions")

    if verbose:
        for qid, verdict, pts in details:
            if verdict == "wrong":
                gold = gold_index[qid]
                pred = sub_index.get(qid, {})
                print(f"  WRONG {qid}: gold={gold['type']}:{gold['answer']}  pred={pred.get('type')}:{pred.get('answer')}")

    return score_val


def self_check(split_root: Path):
    """Score gold answers against themselves — should be perfect."""
    answers_path = split_root / "answers.jsonl"
    with open(answers_path, encoding="utf-8") as f:
        lines = f.readlines()

    # Build submission from gold (convert unanswerable null → type=unanswerable)
    sub_lines = []
    for line in lines:
        item = json.loads(line)
        if item["answer"] is None:
            sub_lines.append(json.dumps({"id": item["id"], "type": "unanswerable", "answer": "unanswerable"}, ensure_ascii=False))
        else:
            sub_lines.append(json.dumps({"id": item["id"], "type": item["type"], "answer": item["answer"]}, ensure_ascii=False))

    import tempfile, os
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tmp:
        tmp.write("\n".join(sub_lines))
        tmp_path = tmp.name

    result = score(split_root, Path(tmp_path))
    os.unlink(tmp_path)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["train", "public_test"], default="train")
    parser.add_argument("--data-dir", default=None, help="Root dir containing split folders")
    parser.add_argument("--sub", default="submission.jsonl")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    base = Path(args.data_dir) if args.data_dir else Path(__file__).parent.parent
    split_map = {
        "train": base / "train",
        "public_test": base / "infor" / "data" / "public_test",
    }
    split_root = split_map[args.split]

    if not split_root.exists():
        print(f"Split root not found: {split_root}")
        sys.exit(1)

    if args.self_check:
        result = self_check(split_root)
        print(f"\nSelf-check score: {result} (should equal total questions)")
    else:
        score(split_root, Path(args.sub), verbose=args.verbose)
