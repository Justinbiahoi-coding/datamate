#!/usr/bin/env python3
"""Process batches 010-014 with validation against gold answers.

Usage:
  python code/process_batches_010_014.py
  
Environment:
  DATAMATE_LLM_BACKEND: agent (gemini|anthropic|groq|ollama|local)
  ANTHROPIC_API_KEY: for 'anthropic' backend
  GEMINI_API_KEY: for 'gemini' backend
  GROQ_API_KEY: for 'groq' backend
"""
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Set

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from agent import infer
from scorer import match_answer


def load_batch_files(batch_dir: Path, batch_nums: list) -> list:
    """Load questions from batch files (retry7_NNN.jsonl)."""
    questions = []
    for num in batch_nums:
        batch_path = batch_dir / f"retry7_{num:03d}.jsonl"
        if not batch_path.exists():
            print(f"[WARN] batch not found: {batch_path}", flush=True)
            continue
        with open(batch_path, encoding="utf-8") as f:
            count = 0
            for line in f:
                if line.strip():
                    questions.append(json.loads(line))
                    count += 1
            print(f"[LOAD] {batch_path.name}: {count} questions", flush=True)
    return questions


def load_done_ids(sub_path: Path) -> Set[str]:
    """Get IDs already in submission file (resume support)."""
    done = set()
    if sub_path.exists():
        with open(sub_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        done.add(json.loads(line)["id"])
                    except Exception:
                        pass
    return done


def main():
    batch_dir = Path("batches_retry7")
    sub_path = Path("sub_sonnet.jsonl")
    split_root = ROOT / "train"
    batch_nums = [10, 11, 12, 13, 14]

    if not split_root.exists():
        sys.exit(f"[FATAL] split root not found: {split_root}")
    if not (split_root / "rulebook.md").exists():
        sys.exit(f"[FATAL] rulebook not found: {split_root / 'rulebook.md'}")

    # Load rulebook once
    rulebook = (split_root / "rulebook.md").read_text(encoding="utf-8")

    # Load batches
    questions = load_batch_files(batch_dir, batch_nums)
    print(f"[QUEST] {len(questions)} questions total\n", flush=True)

    # Resume: skip done IDs
    done_ids = load_done_ids(sub_path)
    if done_ids:
        questions = [q for q in questions if q["id"] not in done_ids]
        print(f"[RESUME] {len(done_ids)} already done, {len(questions)} remaining\n", flush=True)

    # Process
    n_correct = n_wrong = n_abs = 0
    t_start = time.time()
    mode = "a" if done_ids else "w"

    with open(sub_path, mode, encoding="utf-8") as fout:
        for i, item in enumerate(questions):
            qid = item["id"]
            t0 = time.time()

            try:
                result = infer(item, split_root, rulebook)
            except Exception as e:
                result = {"id": qid, "type": "abstain", "answer": None, "_err": f"fatal:{str(e)[:150]}"}
                traceback.print_exc(file=sys.stderr)

            # Validate against gold answer if available
            gold_type = item.get("_gold_type")
            gold_ans = item.get("_gold_answer")
            gold_alias = item.get("_gold_alias", [])
            
            verdict = "abstain"
            if result.get("type") != "abstain" and gold_type:
                if match_answer(result.get("type"), result.get("answer"), gold_type, gold_ans, gold_alias):
                    verdict = "correct"
                    n_correct += 1
                else:
                    verdict = "wrong"
                    n_wrong += 1
            else:
                n_abs += 1
            
            # Add validation info
            result["_attempts"] = 1  # TODO: track retry attempts
            result["_verdict"] = verdict

            # Write submission format (keep internal keys for now, will strip for final submission)
            fout.write(json.dumps(result, ensure_ascii=False,
                                  default=lambda o: o.item() if hasattr(o, 'item') else str(o)) + "\n")
            fout.flush()

            elapsed = time.time() - t0

            # Progress every 5
            if (i + 1) % 5 == 0:
                total_elapsed = time.time() - t_start
                rate = (i + 1) / total_elapsed
                eta = (len(questions) - i - 1) / rate if rate > 0 else 0
                print(f"  [{i+1}/{len(questions)}]  correct={n_correct} wrong={n_wrong} abs={n_abs}  "
                      f"{rate:.2f}q/s  ETA={eta/60:.0f}m", flush=True)

    total_elapsed = time.time() - t_start
    total_acc = (n_correct) / (n_correct + n_wrong) * 100 if (n_correct + n_wrong) > 0 else 0
    print(f"\n{'='*60}")
    print(f"[DONE] {total_elapsed/60:.1f}m  correct={n_correct} wrong={n_wrong} abstain={n_abs}")
    print(f"[ACC]  {total_acc:.1f}% ({n_correct}/{n_correct+n_wrong})")
    print(f"[OUT]  {sub_path}  ({n_correct + n_wrong + n_abs} new lines)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
