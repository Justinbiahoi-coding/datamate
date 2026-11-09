#!/usr/bin/env python3
"""Process retry7 batches using pattern matching from successful examples."""
import json
import sys
from pathlib import Path
from typing import Optional, Dict, List

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "code"))

from loader import load_business
from agent import exec_code, infer_type
from scorer import match_answer


def load_batch_questions() -> Dict[str, dict]:
    """Load all retry7 questions."""
    questions = {}
    for i in range(5):
        fname = ROOT / "batches_retry7" / f"retry7_{i:03d}.jsonl"
        if not fname.exists():
            continue
        with open(fname) as f:
            for line in f:
                obj = json.loads(line)
                questions[obj["id"]] = obj
    return questions


def load_reference_data() -> tuple:
    """Load existing solutions from sub_sonnet.jsonl as reference.
    
    Returns: (existing_ids_set, question_to_solution_map)
    """
    existing_ids = set()
    solutions_by_biz = {}  # business_id -> list of (question_keywords, code)
    
    # Since sub_sonnet.jsonl doesn't have business_id, we need to get it from original questions
    # First, build a map of all question IDs in the train set
    all_train_qs = {}
    train_qs_file = ROOT / "train" / "questions.jsonl"
    if train_qs_file.exists():
        with open(train_qs_file) as f:
            for line in f:
                obj = json.loads(line)
                all_train_qs[obj["id"]] = obj
    
    # Now load sub_sonnet and map to business_ids
    with open(ROOT / "sub_sonnet.jsonl") as f:
        for line in f:
            obj = json.loads(line)
            qid = obj["id"]
            existing_ids.add(qid)
            
            # Try to find business_id from train data
            if qid in all_train_qs:
                biz_id = all_train_qs[qid].get("business_id")
                if biz_id and "_code" in obj and obj["_verdict"] == "correct":
                    if biz_id not in solutions_by_biz:
                        solutions_by_biz[biz_id] = []
                    # Extract question keywords
                    q_text = all_train_qs[qid].get("question", "")
                    solutions_by_biz[biz_id].append({
                        "question": q_text,
                        "code": obj["_code"],
                        "type": obj.get("type"),
                        "answer": obj.get("answer")
                    })
    
    return existing_ids, solutions_by_biz


def find_similar_code(question: str, biz_id: str, solutions_by_biz: Dict) -> Optional[str]:
    """Find similar code from successful solutions for the same business."""
    if biz_id not in solutions_by_biz:
        return None
    
    # Check if question patterns match
    q_lower = question.lower()
    q_keywords = set(w for w in q_lower.split() if len(w) > 3)
    
    best_score = 0
    best_code = None
    
    for sol in solutions_by_biz[biz_id]:
        sol_q = sol["question"].lower()
        sol_keywords = set(w for w in sol_q.split() if len(w) > 3)
        
        # Overlap score
        overlap = len(q_keywords & sol_keywords) / max(1, min(len(q_keywords), len(sol_keywords)))
        
        if overlap > best_score:
            best_score = overlap
            best_code = sol["code"]
    
    # Return code only if similarity is reasonable
    return best_code if best_score > 0.4 else None


def process_all():
    """Process all retry7 questions."""
    print("Loading data...")
    batch_qs = load_batch_questions()
    existing_ids, solutions_by_biz = load_reference_data()
    
    print(f"Loaded {len(batch_qs)} batch questions")
    print(f"Found {len(solutions_by_biz)} businesses with successful solutions")
    
    results = []
    correct_count = 0
    wrong_count = 0
    abstain_count = 0
    
    for qid, item in batch_qs.items():
        if qid in existing_ids:
            print(f"⊘ {qid} already exists")
            continue
        
        biz_id = item["business_id"]
        question = item["question"]
        as_of_date = item["as_of_date"]
        gold_type = item.get("_gold_type")
        gold_answer = item.get("_gold_answer")
        gold_alias = item.get("_gold_alias", [])
        
        # Try to find similar code
        template_code = find_similar_code(question, biz_id, solutions_by_biz)
        
        if not template_code:
            # No template found, abstain
            results.append({
                "id": qid,
                "type": "unanswerable",
                "answer": None,
                "_code": f"# No template for {biz_id}",
                "_attempts": 1,
                "_verdict": "abstain"
            })
            abstain_count += 1
            print(f"⊘ {qid} (abstain - no template)")
            continue
        
        # Load business data and try to execute template code
        try:
            split_root = ROOT / "train"
            biz_dir = split_root / "data" / biz_id
            if not biz_dir.exists():
                results.append({
                    "id": qid,
                    "type": "unanswerable",
                    "answer": None,
                    "_code": "# Data not found",
                    "_attempts": 1,
                    "_verdict": "abstain"
                })
                abstain_count += 1
                print(f"⊘ {qid} (abstain - data not found)")
                continue
            
            biz_data = load_business(biz_dir)
            
            # Try to execute the template code
            answer = exec_code(template_code, biz_data, as_of_date)
            pred_type = infer_type(answer) if answer is not None else "unanswerable"
            
            # Validate
            is_correct = match_answer(pred_type, answer, gold_type, gold_answer, gold_alias)
            
            results.append({
                "id": qid,
                "type": pred_type,
                "answer": answer,
                "_code": template_code,
                "_attempts": 1,
                "_verdict": "correct" if is_correct else "wrong"
            })
            
            if is_correct:
                correct_count += 1
                print(f"✓ {qid}")
            else:
                wrong_count += 1
                print(f"✗ {qid} (expected {gold_answer}, got {answer})")
        
        except Exception as e:
            results.append({
                "id": qid,
                "type": "unanswerable",
                "answer": None,
                "_code": template_code,
                "_attempts": 1,
                "_verdict": "abstain"
            })
            abstain_count += 1
            print(f"⊘ {qid} (error: {str(e)[:50]})")
    
    # Append to sub_sonnet.jsonl
    if results:
        with open(ROOT / "sub_sonnet.jsonl", "a") as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
        
        print(f"\n✓ Processed {len(results)} questions")
        print(f"  Correct: {correct_count}")
        print(f"  Wrong: {wrong_count}")
        print(f"  Abstain: {abstain_count}")
    else:
        print("\nNo new results to process")


if __name__ == "__main__":
    process_all()
