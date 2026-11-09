"""Chia problematic_questions.jsonl thành các batch nhỏ để subagents xử lý song song.

Usage:
  python prepare_batch.py --size 25 --out-dir batches/
    → batches/batch_000.jsonl, batch_001.jsonl, ...
  python prepare_batch.py --size 10 --mix-types --limit 10 --out-dir pilot/
    → pilot/batch_000.jsonl với 10 câu mix types (pilot)
"""
import json, argparse, random
from pathlib import Path


def main():
    ROOT = Path(__file__).parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default=str(ROOT / "problematic_questions.jsonl"))
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--size", type=int, default=25, help="câu/batch")
    parser.add_argument("--mix-types", action="store_true",
                        help="prioritize đa dạng type trong 1 batch")
    parser.add_argument("--limit", type=int, default=None, help="chỉ lấy N câu đầu")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(args.src, encoding="utf-8") as f:
        items = [json.loads(l) for l in f if l.strip()]

    rng = random.Random(args.seed)

    if args.mix_types:
        # Group by type, interleave
        by_type = {}
        for it in items:
            by_type.setdefault(it.get("_gold_type", "number"), []).append(it)
        for t in by_type:
            rng.shuffle(by_type[t])
        # Interleave: 1 from each type round-robin
        interleaved = []
        while any(by_type.values()):
            for t in sorted(by_type):
                if by_type[t]:
                    interleaved.append(by_type[t].pop(0))
        items = interleaved
    else:
        rng.shuffle(items)

    if args.limit:
        items = items[:args.limit]

    n_batches = 0
    for i in range(0, len(items), args.size):
        batch = items[i:i + args.size]
        out_path = out_dir / f"batch_{n_batches:03d}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for it in batch:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        n_batches += 1

    # Type stats for created batches
    print(f"Created {n_batches} batches in {out_dir}/  (size={args.size}, total={len(items)} câu)")
    types = {}
    for it in items:
        t = it.get("_gold_type", "unknown")
        types[t] = types.get(t, 0) + 1
    for t in sorted(types):
        print(f"  {t:<14} {types[t]}")


if __name__ == "__main__":
    main()
