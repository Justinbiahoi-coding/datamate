#!/usr/bin/env python3
"""Validate batch gold answers and show statistics."""
import json
from pathlib import Path

batch_dir = Path("batches_retry7")
batch_nums = [10, 11, 12, 13, 14]

# Load all questions
all_questions = []
for num in batch_nums:
    batch_path = batch_dir / f"retry7_{num:03d}.jsonl"
    with open(batch_path) as f:
        for line in f:
            if line.strip():
                all_questions.append(json.loads(line))

# Analyze
print(f"Total questions: {len(all_questions)}")
print(f"\nAnswer types:")
types = {}
for q in all_questions:
    t = q.get("_gold_type")
    types[t] = types.get(t, 0) + 1
    
for t in sorted(types):
    print(f"  {t:15} {types[t]:3}")

# Sample a few
print(f"\nSample questions:")
for q in all_questions[:3]:
    print(f"  ID: {q['id']}")
    print(f"    Q:  {q['question'][:60]}...")
    print(f"    Ans: {q.get('_gold_answer')}")
    print()
