#!/usr/bin/env python3
"""Process batches 010-014 with validation against gold answers.

Batches: retry7_010.jsonl through retry7_014.jsonl (125 questions)
Output: Append to sub_sonnet.jsonl with validation (_verdict, _attempts)

Setup required:
  DATAMATE_LLM_BACKEND=anthropic
  ANTHROPIC_API_KEY=<your-key>

Or other backends:
  DATAMATE_LLM_BACKEND=gemini GEMINI_API_KEY=<key>
  DATAMATE_LLM_BACKEND=groq GROQ_API_KEY=<key>

Usage:
  ANTHROPIC_API_KEY=... python3 code/process_batches_010_014_v2.py
  
Environment defaults:
  - Split: train
  - Output: sub_sonnet.jsonl (append mode)
  - Batches: retry7_010..014
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
                    q = json.loads(line)
                    # Keep gold answer for validation
                    q['_gold_type'] = q.get('_gold_type')
                    q['_gold_answer'] = q.get('_gold_answer')
                    q['_gold_alias'] = q.get('_gold_alias', [])
                    questions.append(q)
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
    import os
    
    batch_dir = Path("batches_retry7")
    sub_path = Path("sub_sonnet.jsonl")
    split_root = ROOT / "train"
    batch_nums = [10, 11, 12, 13, 14]

    if not split_root.exists():
        sys.exit(f"[FATAL] split root not found: {split_root}")
    if not (split_root / "rulebook.md").exists():
        sys.exit(f"[FATAL] rulebook not found: {split_root / 'rulebook.md'}")

    # Check backend
    backend = os.environ.get("DATAMATE_LLM_BACKEND", "")
    if not backend:
        print("[WARN] DATAMATE_LLM_BACKEND not set, will use abstain fallback", flush=True)
        print("       Set: ANTHROPIC_API_KEY + DATAMATE_LLM_BACKEND=anthropic", flush=True)

    # Load rulebook once
    rulebook = (split_root / "rulebook.md").read_text(encoding="utf-8")

    # Load batches
    questions = load_batch_files(batch_dir, batch_nums)
    print(f"\n[QUEST] {len(questions)} questions total\n", flush=True)

    if not questions:
        print("[ABORT] No questions found", flush=True)
        sys.exit(1)

    # Resume: skip done IDs
    done_ids = load_done_ids(sub_path)
    remaining = [q for q in questions if q["id"] not in done_ids]
    if done_ids:
        print(f"[RESUME] {len(done_ids)} already done, {len(remaining)} remaining\n", flush=True)
    else:
        print(f"[NEW] {len(remaining)} new questions\n", flush=True)

    if not remaining:
        print("[DONE] All questions already processed", flush=True)
        return

    # Process
    n_correct = n_wrong = n_abs = n_err = 0
    t_start = time.time()
    mode = "a" if done_ids else "w"

    print(f"[START] Processing {len(remaining)} questions...\n", flush=True)

    with open(sub_path, mode, encoding="utf-8") as fout:
        for i, item in enumerate(remaining):
            qid = item["id"]
            t0 = time.time()

            try:
                result = infer(item, split_root, rulebook)
                err = False
            except Exception as e:
                result = {"id": qid, "type": "abstain", "answer": None, "_err": f"fatal:{str(e)[:150]}"}
                err = True
                n_err += 1
                traceback.print_exc(file=sys.stderr)

            # Validate against gold answer
            gold_type = item.get("_gold_type")
            gold_ans = item.get("_gold_answer")
            gold_alias = item.get("_gold_alias", [])
            
            verdict = "abstain"
            if not err and result.get("type") != "abstain" and gold_type:
                try:
                    if match_answer(result.get("type"), result.get("answer"), gold_type, gold_ans, gold_alias):
                        verdict = "correct"
                        n_correct += 1
                    else:
                        verdict = "wrong"
                        n_wrong += 1
                except Exception:
                    verdict = "abstain"
                    n_abs += 1
            else:
                n_abs += 1
            
            # Add validation info
            result["_attempts"] = 1
            result["_verdict"] = verdict

            # Write output
            fout.write(json.dumps(result, ensure_ascii=False,
                                  default=lambda o: o.item() if hasattr(o, 'item') else str(o)) + "\n")
            fout.flush()

            elapsed = time.time() - t0

            # Progress every 5 questions
            if (i + 1) % 5 == 0:
                total_elapsed = time.time() - t_start
                rate = (i + 1) / total_elapsed
                eta = (len(remaining) - i - 1) / rate if rate > 0 else 0
                print(f"  [{i+1:3}/{len(remaining):3}]  ✓={n_correct:3} ✗={n_wrong:3} ○={n_abs:3} E={n_err:2}  "
                      f"{rate:.2f}q/s  ETA={eta/60:5.1f}m", flush=True)

    total_elapsed = time.time() - t_start
    total_answered = n_correct + n_wrong
    total_acc = (n_correct / total_answered * 100) if total_answered > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"[SUMMARY] Total time: {total_elapsed/60:.1f}m")
    print(f"          Correct:   {n_correct:3} / {total_answered:3}  ({total_acc:5.1f}%)")
    print(f"          Wrong:     {n_wrong:3} / {total_answered:3}")
    print(f"          Abstain:   {n_abs:3}")
    print(f"          Errors:    {n_err:3}")
    print(f"[OUTPUT]  {sub_path.absolute()}")
    print(f"          {len(remaining)} new questions appended")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
