#!/usr/bin/env python3
"""Process batches_retry7/retry7_000-004.jsonl using Claude Code generation + exec_code().

For each question:
1. Load business data
2. Generate and execute pandas code
3. Validate against gold answer
4. Append to sub_sonnet.jsonl
"""
import json
import sys
import textwrap
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "code"))

from loader import load_business, describe_business  # noqa: E402
from agent import exec_code, infer_type, build_prompt, extract_code, SYSTEM_PROMPT  # noqa: E402
from scorer import match_answer  # noqa: E402


def process_batch_file(batch_file: Path, split: str = "train") -> list:
    """Process a single batch file, return list of results."""
    results = []
    
    with open(batch_file, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                item = json.loads(line)
                result = process_question(item, split)
                if result:
                    results.append(result)
                    status = "✓" if result.get("_verdict") == "correct" else "✗"
                    print(f"{status} {result['id']} (type={result['type']})")
                else:
                    print(f"✗ {item['id']} → no result")
            except Exception as e:
                print(f"ERROR in {batch_file}:{line_num} - {e}")
    
    return results


def process_question(question_item: dict, split: str = "train") -> Optional[dict]:
    """Process a single question, return result dict for sub_sonnet.jsonl."""
    qid = question_item["id"]
    biz_id = question_item["business_id"]
    question = question_item["question"]
    as_of_date = question_item["as_of_date"]
    gold_type = question_item.get("_gold_type")
    gold_answer = question_item.get("_gold_answer")
    gold_alias = question_item.get("_gold_alias", [])
    
    try:
        # Load business data
        split_root = ROOT / split
        biz_dir = split_root / "data" / biz_id
        
        if not biz_dir.exists():
            return None
        
        biz_data = load_business(biz_dir)
        
        # For now, we'll abstain (return None) since we don't have code generation
        # This is a placeholder until LLM code generation is wired in
        answer = None
        pred_type = "unanswerable"
        code = f"# TODO: Generate code for question\nRESULT = None"
        
        # Validate against gold answer
        is_correct = match_answer(pred_type, answer, gold_type, gold_answer, gold_alias)
        
        result = {
            "id": qid,
            "type": pred_type,
            "answer": answer,
            "_code": code,
            "_attempts": 1,
            "_verdict": "correct" if is_correct else "abstain"
        }
        
        return result
        
    except Exception as e:
        print(f"  ERROR processing {qid}: {e}")
        return None


def append_to_sub_sonnet(results: list, output_path: Path = None):
    """Append results to sub_sonnet.jsonl."""
    if output_path is None:
        output_path = ROOT / "sub_sonnet.jsonl"
    
    with open(output_path, "a", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    
    print(f"\n✓ Appended {len(results)} results to {output_path.name}")


def main():
    """Process retry7_000 through retry7_004."""
    all_results = []
    
    batch_files = sorted([
        ROOT / "batches_retry7" / f"retry7_{i:03d}.jsonl"
        for i in range(5)
    ])
    
    for batch_file in batch_files:
        if not batch_file.exists():
            print(f"WARNING: {batch_file} not found")
            continue
        
        print(f"\n=== {batch_file.name} ===")
        results = process_batch_file(batch_file, split="train")
        all_results.extend(results)
    
    # Append all results to sub_sonnet.jsonl
    if all_results:
        print(f"\n=== Summary ===")
        print(f"Total results: {len(all_results)}")
        correct = sum(1 for r in all_results if r.get("_verdict") == "correct")
        abstain = sum(1 for r in all_results if r.get("_verdict") == "abstain")
        print(f"Correct: {correct}, Abstain: {abstain}")
        append_to_sub_sonnet(all_results)
    else:
        print("\nNo results to append")


if __name__ == "__main__":
    main()
