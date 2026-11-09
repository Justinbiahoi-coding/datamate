#!/usr/bin/env python3
"""Smart code generator for DataMate questions using business schema understanding."""
import json
import sys
import re
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "code"))

from loader import load_business, describe_business
from agent import exec_code, infer_type
from scorer import match_answer


def analyze_question(question: str, as_of_date: str) -> dict:
    """Analyze a Vietnamese question to extract intent."""
    q_lower = question.lower()
    
    # Detect answer type based on keywords
    is_count = any(x in q_lower for x in ['mấy', 'bao nhiêu', 'số', 'cái', 'chiếc', 'đơn'])
    is_revenue = any(x in q_lower for x in ['tiền', 'doanh thu', 'bán được', 'bán dc', 'bán đc'])
    is_date = any(x in q_lower for x in ['ngày', 'khi nào', 'lúc nào'])
    is_percent = any(x in q_lower for x in ['tỷ lệ', 'tỉ lệ', 'phần trăm', '%'])
    is_average = any(x in q_lower for x in ['bình quân', 'trung bình', 'bình quân cộng'])
    
    # Detect time scope
    is_today = any(x in q_lower for x in ['hôm nay', 'hnay', 'hôm nay', 'ngày hôm nay', 'ngay hom nay'])
    is_month = any(x in q_lower for x in ['tháng', 'thang'])
    is_week = any(x in q_lower for x in ['tuần', 'tuan'])
    
    # Detect product filtering
    has_product = any(x in question for x in ['thuốc', 'OMO', 'Bột', 'Nước', 'xi măng', 'Sữa']) or 'sp ' in q_lower or 'sản phẩm' in q_lower
    
    return {
        'is_count': is_count,
        'is_revenue': is_revenue,
        'is_date': is_date,
        'is_percent': is_percent,
        'is_average': is_average,
        'is_today': is_today,
        'is_month': is_month,
        'is_week': is_week,
        'has_product': has_product,
    }


def generate_code_smart(question: str, as_of_date: str, biz_data: dict, 
                        biz_schema: str) -> Optional[str]:
    """Generate pandas code by understanding the question and business structure."""
    
    intent = analyze_question(question, as_of_date)
    
    # Check what data tables are available
    tables = [k for k in biz_data.keys() if not k.startswith('_')]
    
    # Try to find main transaction table (sales/invoices)
    sales_table = None
    for t in tables:
        t_lower = t.lower()
        if any(x in t_lower for x in ['ban_hang', 'hoa_don', 'invoice', 'sales', 'order']):
            sales_table = t
            break
    
    # If not found, use first non-multi-sheet table
    if not sales_table and tables:
        for t in tables:
            v = biz_data[t]
            if not isinstance(v, dict):  # not a multi-sheet file
                sales_table = t
                break
    
    if not sales_table:
        return None
    
    # Generate basic code structure
    code_parts = []
    code_parts.append(f"df = {sales_table}.copy() if '{sales_table}' in dir() else None")
    code_parts.append("if df is not None:")
    code_parts.append("  # Parse dates")
    code_parts.append("  for col in df.columns:")
    code_parts.append("    if 'ngay' in col.lower() or 'date' in col.lower() or 'gio' in col.lower():")
    code_parts.append("      df[col] = parse_date(df[col])")
    code_parts.append("      break")
    code_parts.append(""  )
    code_parts.append("  # Filter cancelled/returned orders if status column exists")
    code_parts.append("  status_cols = [c for c in df.columns if 'trang' in c.lower() or 'status' in c.lower() or 'ghi_chu' in c.lower()]")
    code_parts.append("  if status_cols:")
    code_parts.append("    df = df[~df[status_cols[0]].str.contains('hủy|huỷ|trả|hoàn', case=False, na=False)]")
    
    # Filter by date based on intent
    if intent['is_today']:
        code_parts.append(f"  df = df[df.iloc[:, 0].dt.date == pd.to_datetime('{as_of_date}').date()]  # Today")
    elif intent['is_month']:
        code_parts.append(f"  as_of = pd.to_datetime('{as_of_date}')")
        code_parts.append(f"  df = df[(df.iloc[:, 0].dt.year == as_of.year) & (df.iloc[:, 0].dt.month == as_of.month)]")
    
    # Generate aggregation based on intent
    if intent['is_revenue']:
        code_parts.append("  # Sum revenue")
        code_parts.append("  rev_col = find_revenue_col(df)")
        code_parts.append("  if rev_col:")
        code_parts.append("    RESULT = int(to_num(df[rev_col]).sum())")
        code_parts.append("  else:")
        code_parts.append("    RESULT = 0")
    elif intent['is_count']:
        code_parts.append("  # Count records")
        code_parts.append("  RESULT = len(df)")
    
    code_parts.append("else:")
    code_parts.append("  RESULT = None")
    
    return "\n".join(code_parts)


def process_question(item: dict, split: str = "train") -> Optional[dict]:
    """Process a question and return result."""
    qid = item["id"]
    biz_id = item["business_id"]
    question = item["question"]
    as_of_date = item["as_of_date"]
    gold_type = item.get("_gold_type")
    gold_answer = item.get("_gold_answer")
    gold_alias = item.get("_gold_alias", [])
    
    try:
        # Load business data
        split_root = ROOT / split
        biz_dir = split_root / "data" / biz_id
        if not biz_dir.exists():
            return None
        
        biz_data = load_business(biz_dir)
        biz_schema = describe_business(biz_data, biz_dir)
        
        # Generate code
        code = generate_code_smart(question, as_of_date, biz_data, biz_schema)
        if not code:
            return {
                "id": qid,
                "type": "unanswerable",
                "answer": None,
                "_code": "# No suitable table found",
                "_attempts": 1,
                "_verdict": "abstain"
            }
        
        # Execute code
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
        return {
            "id": qid,
            "type": "unanswerable",
            "answer": None,
            "_code": f"# Error: {str(e)}",
            "_attempts": 1,
            "_verdict": "error"
        }


def main():
    """Process retry7 batches."""
    all_results = []
    
    batch_files = sorted([
        ROOT / "batches_retry7" / f"retry7_{i:03d}.jsonl"
        for i in range(5)
    ])
    
    for batch_file in batch_files:
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
        wrong = sum(1 for r in all_results if r["_verdict"] == "wrong")
        abstain = sum(1 for r in all_results if r["_verdict"] == "abstain")
        
        print(f"\n✓ Processed {len(all_results)} questions")
        print(f"  Correct: {correct}, Wrong: {wrong}, Abstain: {abstain}")
    else:
        print("\nNo results generated")


if __name__ == "__main__":
    main()
