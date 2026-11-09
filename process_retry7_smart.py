#!/usr/bin/env python3
"""Smart processing of retry7 batches using schema understanding."""
import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "code"))

from loader import load_business, describe_business
from agent import exec_code, infer_type
from scorer import match_answer


def generate_smart_code(question: str, as_of_date: str, biz_id: str, 
                        biz_data: dict, biz_schema: str) -> Optional[str]:
    """Generate code by understanding question intent and business schema."""
    
    q_lower = question.lower()
    tables = list(biz_data.keys())
    
    # Determine question type and what aggregation is needed
    is_revenue = any(x in q_lower for x in ['tiền', 'doanh thu', 'bán đc', 'bán được'])
    is_count = any(x in q_lower for x in ['bao nhiêu', 'mấy', 'số', 'cái'])
    is_debt = any(x in q_lower for x in ['nợ', 'công nợ', 'còn lại'])
    is_avg = any(x in q_lower for x in ['bình quân', 'trung bình'])
    has_date_filter = any(x in q_lower for x in ['tháng', 'ngày', 'hôm', 'tuần', 'năm', 'tết'])
    
    # Find main transaction table
    table_name = None
    for t in tables:
        t_lower = t.lower()
        if any(x in t_lower for x in ['ban_hang', 'hoa_don', 'invoice', 'don_hang', 'order']):
            table_name = t
            break
    
    if not table_name:
        # Try to find any CSV/Excel table
        for t in tables:
            if not isinstance(biz_data.get(t), dict):
                table_name = t
                break
    
    if not table_name:
        return None
    
    # Start building code
    code_lines = []
    
    # Try common approach: load table, filter, aggregate
    if isinstance(biz_data.get(table_name), dict):
        # Multi-sheet, use __all version
        code_lines.append(f"df = {table_name}__all.copy() if '{table_name}__all' in dir() else {table_name}[list({table_name}.keys())[0]].copy()")
    else:
        code_lines.append(f"df = {table_name}.copy() if '{table_name}' in dir() else None")
    
    code_lines.append("if df is not None:")
    
    # Parse dates
    code_lines.append("  # Find and parse date column")
    code_lines.append("  date_col = None")
    code_lines.append("  for col in df.columns:")
    code_lines.append("    if any(x in col.lower() for x in ['ngay', 'date', 'gio', 'thoi']):")
    code_lines.append("      date_col = col")
    code_lines.append("      df[col] = parse_date(df[col])")
    code_lines.append("      break")
    
    # Filter cancelled/returned
    code_lines.append("  # Filter valid orders (remove cancelled/returned)")
    code_lines.append("  for col in df.columns:")
    code_lines.append("    if any(x in col.lower() for x in ['status', 'trang', 'ghi_chu']):")
    code_lines.append("      df = df[~df[col].str.contains('hủy|huỷ|trả', case=False, na=False)]")
    code_lines.append("      break")
    
    # Date filtering
    if has_date_filter:
        code_lines.append(f"  # Filter by date")
        code_lines.append(f"  as_of = pd.to_datetime('{as_of_date}')")
        code_lines.append(f"  if date_col:")
        code_lines.append(f"    df = df[df[date_col].dt.date <= as_of.date()]")
    
    # Generate aggregation
    if is_debt:
        # Count customers with debt
        code_lines.append("  # Count customers with debt")
        code_lines.append("  for col in df.columns:")
        code_lines.append("    if any(x in col.lower() for x in ['no', 'con_lai', 'debt', 'remaining']):")
        code_lines.append("      debt_col = col")
        code_lines.append("      break")
        code_lines.append("  else:")
        code_lines.append("    debt_col = None")
        code_lines.append("  if debt_col:")
        code_lines.append("    for col in df.columns:")
        code_lines.append("      if any(x in col.lower() for x in ['kh', 'customer', 'khach']):")
        code_lines.append("        cust_col = col")
        code_lines.append("        RESULT = df[to_num(df[debt_col]) > 0][cust_col].nunique()")
        code_lines.append("        break")
    
    elif is_revenue:
        # Sum revenue
        code_lines.append("  # Sum revenue")
        code_lines.append("  rev_col = find_revenue_col(df)")
        code_lines.append("  if rev_col:")
        code_lines.append("    RESULT = int(to_num(df[rev_col]).sum())")
    
    elif is_count and 'order' not in q_lower:
        # Count rows/items
        code_lines.append("  # Count items")
        code_lines.append("  RESULT = len(df)")
    
    else:
        code_lines.append("  RESULT = None")
    
    code_lines.append("else:")
    code_lines.append("  RESULT = None")
    
    return "\n".join(code_lines)


def process_question(item: dict) -> Optional[dict]:
    """Process a single question."""
    qid = item["id"]
    biz_id = item["business_id"]
    question = item["question"]
    as_of_date = item["as_of_date"]
    gold_type = item.get("_gold_type")
    gold_answer = item.get("_gold_answer")
    gold_alias = item.get("_gold_alias", [])
    
    try:
        # Load business data
        split_root = ROOT / "train"
        biz_dir = split_root / "data" / biz_id
        if not biz_dir.exists():
            return None
        
        biz_data = load_business(biz_dir)
        biz_schema = describe_business(biz_data, biz_dir)
        
        # Generate smart code
        code = generate_smart_code(question, as_of_date, biz_id, biz_data, biz_schema)
        if not code:
            return None
        
        # Execute
        answer = exec_code(code, biz_data, as_of_date)
        pred_type = infer_type(answer) if answer is not None else "unanswerable"
        
        # Validate
        is_correct = match_answer(pred_type, answer, gold_type, gold_answer, gold_alias)
        
        return {
            "id": qid,
            "type": pred_type,
            "answer": answer,
            "_code": code,
            "_attempts": 1,
            "_verdict": "correct" if is_correct else "wrong"
        }
        
    except Exception as e:
        return None


def main():
    """Process all retry7 batches."""
    all_results = []
    
    for i in range(5):
        batch_file = ROOT / "batches_retry7" / f"retry7_{i:03d}.jsonl"
        if not batch_file.exists():
            continue
        
        print(f"\nProcessing {batch_file.name}...")
        
        with open(batch_file) as f:
            for line in f:
                item = json.loads(line)
                result = process_question(item)
                if result:
                    all_results.append(result)
                    status = "✓" if result["_verdict"] == "correct" else "✗"
                    print(f"  {status} {result['id']}")
    
    # Append to sub_sonnet.jsonl
    if all_results:
        with open(ROOT / "sub_sonnet.jsonl", "a") as f:
            for result in all_results:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
        
        correct = sum(1 for r in all_results if r["_verdict"] == "correct")
        print(f"\n✓ Processed {len(all_results)} questions, {correct} correct")
    else:
        print("\nNo results")


if __name__ == "__main__":
    main()
