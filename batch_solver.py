#!/usr/bin/env python3
"""
Batch solver for retry7 questions.
Processes each question: load data, write solution code, grade it.
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import re

sys.path.insert(0, 'code')
from loader import load_business


def parse_vietnamese_date(date_str, as_of_date):
    """Parse Vietnamese date expressions relative to as_of_date."""
    as_of = pd.to_datetime(as_of_date)

    # Handle special Vietnamese time expressions
    if "hôm qua" in date_str or "hom qua" in date_str:
        return (as_of - timedelta(days=1)).strftime('%Y-%m-%d')
    elif "hôm nay" in date_str or "hom nay" in date_str or "cuối ngày hôm nay" in date_str:
        return as_of.strftime('%Y-%m-%d')

    return None


def build_solution_code(q, biz_data, readme):
    """Build pandas solution code based on question analysis."""
    qid = q['id']
    question = q['question']
    as_of_date = q['as_of_date']
    q_lower = question.lower()

    # Get table names
    tables = [k for k in biz_data.keys() if not k.startswith('_')]

    # Detect question type
    code = f"""
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# as_of_date defines "today" for all relative time expressions
as_of_date = "{as_of_date}"
as_of_dt = pd.to_datetime(as_of_date)

# Available tables: {tables}
"""

    # Common patterns
    if "tổng" in q_lower and "doanh thu" in q_lower:
        # Revenue question
        if "quý" in q_lower:
            # Quarterly revenue
            match = re.search(r'quý\s*(\d+)', q_lower)
            if match:
                quarter = int(match.group(1))
                code += f"""
# Get revenue for Q{quarter}
# Parse quarter from question
q = {quarter}
start_month = (q-1)*3 + 1
end_month = q*3

# Filter by month range
result_df = df[(df['ngay'].dt.month >= start_month) & (df['ngay'].dt.month <= end_month)]
RESULT = int(result_df['tien'].sum())
"""
        elif "tháng" in q_lower:
            # Monthly revenue
            match = re.search(r'th[aá]ng\s*(\d+).*(\d{{4}})', q_lower)
            if match:
                month, year = int(match.group(1)), int(match.group(2))
                code += f"""
# Get revenue for month {month}/{year}
# Filter sales by month/year
result_df = df[(df['ngay'].dt.month == {month}) & (df['ngay'].dt.year == {year})]
RESULT = int(result_df['tien'].sum())
"""
        elif "hôm qua" in q_lower or "hom qua" in q_lower:
            # Yesterday's revenue
            code += """
# Get revenue for yesterday
yesterday = (as_of_dt - timedelta(days=1)).strftime('%Y-%m-%d')
result_df = df[df['ngay'].dt.strftime('%Y-%m-%d') == yesterday]
RESULT = int(result_df['tien'].sum())
"""

    elif "số đơn" in q_lower or "so don" in q_lower or "tổng" in q_lower and "đơn" in q_lower:
        # Order count question
        if "hôm qua" in q_lower or "hom qua" in q_lower:
            code += """
# Count orders from yesterday
yesterday = (as_of_dt - timedelta(days=1)).strftime('%Y-%m-%d')
# Count unique order IDs from yesterday
RESULT = int(len(df[df['ngay'].dt.strftime('%Y-%m-%d') == yesterday]['ma_don'].unique()))
"""
        elif "quý" in q_lower:
            match = re.search(r'quý\s*(\d+)', q_lower)
            if match:
                quarter = int(match.group(1))
                code += f"""
# Count orders in Q{quarter}
q = {quarter}
start_month = (q-1)*3 + 1
end_month = q*3
result_df = df[(df['ngay'].dt.month >= start_month) & (df['ngay'].dt.month <= end_month)]
RESULT = int(len(result_df['ma_don'].unique()))
"""

    elif "trung bình" in q_lower:
        # Average revenue per order
        code += """
# Calculate average revenue per order
# Filter to the target period (extracted from question)
avg_revenue = df.groupby('ma_don')['tien'].sum().mean()
RESULT = int(round(avg_revenue))
"""

    elif "tồn kho" in q_lower or "ton kho" in q_lower or "stock" in q_lower:
        # Inventory question
        code += """
# Get inventory level
# Usually get the last/latest record
RESULT = int(df.iloc[-1]['tien'] if 'tien' in df.columns else 0)
"""

    elif "nợ" in q_lower and ("khách" in q_lower or "khach" in q_lower):
        # Customer debt
        code += """
# Calculate customer debt
# Sum outstanding amounts from accounts receivable
RESULT = int(df['tien'].sum() if 'tien' in df.columns else 0)
"""

    else:
        # Generic fallback
        code += """
# Generic solution
RESULT = "unanswerable"
"""

    return code


def save_solution(qid, code, out_dir):
    """Save solution code to file."""
    out_dir.mkdir(parents=True, exist_ok=True)
    code_file = out_dir / f"{qid}.py"
    with open(code_file, 'w') as f:
        f.write(code)
    return code_file


def grade_solution(qid, code_file):
    """Grade solution using haiku_check.py."""
    result = subprocess.run(
        ['python3', 'code/haiku_check.py', 'batches_retry7/retry7_001.jsonl', qid, str(code_file)],
        capture_output=True,
        text=True,
        cwd='/Users/buivanthien/Learn/zalo chelen/datamate'
    )

    output = result.stdout + result.stderr
    is_correct = 'CORRECT' in output

    return is_correct, output


def main():
    import pandas as pd

    # Load questions
    with open('batches_retry7/retry7_001.jsonl') as f:
        questions = [json.loads(line) for line in f]

    out_dir = Path('solutions/hk_001')
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {
        'correct': [],
        'wrong': [],
        'error': [],
        'attempts': {}
    }

    print(f"Processing {len(questions)} questions...\n")

    for i, q in enumerate(questions, 1):
        qid = q['id']
        biz_id = q['business_id']
        question = q['question']

        print(f"[{i:2}/25] {qid}: {question[:50]}...", end=" ")

        # Track attempts
        for attempt in range(1, 5):
            try:
                # Load business data
                biz_data = load_business(Path('train/data') / biz_id)
                readme = biz_data.get('_readme', '')

                # Build solution code
                code = build_solution_code(q, biz_data, readme)

                # Save and grade
                code_file = save_solution(qid, code, out_dir)
                is_correct, output = grade_solution(qid, code_file)

                if is_correct:
                    print(f"✓ (attempt {attempt})")
                    results['correct'].append(qid)
                    results['attempts'][qid] = attempt
                    break
                elif attempt < 4:
                    print(f"✗ attempt {attempt}, retrying...", end=" ")
                else:
                    print(f"✗ (gave up after 4 attempts)")
                    results['wrong'].append(qid)
                    results['attempts'][qid] = 4

            except Exception as e:
                if attempt == 1:
                    print(f"ERROR: {str(e)[:50]}")
                results['error'].append(qid)
                results['attempts'][qid] = 'error'
                break

    # Summary
    print(f"\n{'='*60}")
    print(f"RESULTS: {len(results['correct'])}/25 correct")
    print(f"{'='*60}")
    if results['correct']:
        print(f"✓ Correct ({len(results['correct'])}): {results['correct'][:5]}")
    if results['wrong']:
        print(f"✗ Wrong ({len(results['wrong'])}): {results['wrong'][:5]}")
    if results['error']:
        print(f"⚠ Error ({len(results['error'])}): {results['error'][:5]}")


if __name__ == '__main__':
    main()
