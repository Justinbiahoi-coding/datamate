#!/usr/bin/env python3
"""Process retry batches through standard pipeline: load → code-gen → execute → validate → append.

Reuses agent.infer() with configured LLM backend (env: DATAMATE_LLM_BACKEND).
Supports resume: skips questions already in sub_sonnet.jsonl.

Usage:
  python code/process_retry_batches.py \
    --batch-dir batches_retry7 \
    --batch-nums 30 31 32 33 34 \
    --sub sub_sonnet.jsonl

Or simply:
  python code/process_retry_batches.py
"""
import json
import sys
import argparse
import traceback
import time
from pathlib import Path
from typing import Set

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from agent import infer


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-dir", default="batches_retry7")
    parser.add_argument("--batch-nums", nargs="+", type=int, default=[30, 31, 32, 33, 34])
    parser.add_argument("--sub", default="sub_sonnet.jsonl")
    parser.add_argument("--split", default="train")
    args = parser.parse_args()

    batch_dir = Path(args.batch_dir)
    sub_path = Path(args.sub)
    split_root = ROOT / args.split

    if not split_root.exists():
        sys.exit(f"[FATAL] split root not found: {split_root}")
    if not (split_root / "rulebook.md").exists():
        sys.exit(f"[FATAL] rulebook not found: {split_root / 'rulebook.md'}")

    # Load rulebook once
    rulebook = (split_root / "rulebook.md").read_text(encoding="utf-8")

    # Load batches
    questions = load_batch_files(batch_dir, args.batch_nums)
    print(f"[QUEST] {len(questions)} questions total\n", flush=True)

    # Resume: skip done IDs
    done_ids = load_done_ids(sub_path)
    if done_ids:
        questions = [q for q in questions if q["id"] not in done_ids]
        print(f"[RESUME] {len(done_ids)} already done, {len(questions)} remaining\n", flush=True)

    # Process
    n_ans = n_abs = 0
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

            # Write submission format (no internal keys)
            sub_item = {k: v for k, v in result.items() if not k.startswith("_")}
            fout.write(json.dumps(sub_item, ensure_ascii=False,
                                  default=lambda o: o.item() if hasattr(o, 'item') else str(o)) + "\n")
            fout.flush()

            elapsed = time.time() - t0
            if result.get("type") == "abstain":
                n_abs += 1
            else:
                n_ans += 1

            # Progress every 5
            if (i + 1) % 5 == 0:
                total_elapsed = time.time() - t_start
                rate = (i + 1) / total_elapsed
                eta = (len(questions) - i - 1) / rate if rate > 0 else 0
                print(f"  [{i+1}/{len(questions)}]  ans={n_ans} abs={n_abs}  "
                      f"{rate:.2f}q/s  ETA={eta/60:.0f}m", flush=True)

    total_elapsed = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"[DONE] {total_elapsed/60:.1f}m  answered={n_ans}  abstain={n_abs}")
    print(f"[OUT]  {sub_path}  ({n_ans + n_abs} new lines)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
