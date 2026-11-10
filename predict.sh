#!/bin/bash
set -e

echo "[predict.sh] Khởi động hệ thống DataMate Inference..."
mkdir -p /result/logs

# Gọi script python quản lý việc đọc questions.jsonl và ghi submission.jsonl
python3 -c "
import json, os, time
from src.engine import solve_question

data_dir = '/data'
input_file = os.path.join(data_dir, 'questions.jsonl')
output_submission = '/result/submission.jsonl'

print(f'Bắt đầu xử lý file: {input_file}')
start_time = time.time()

submissions = []
count = 0

if os.path.exists(input_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            q = json.loads(line)
            q_id = q.get('id')

            # Gọi engine giải quyết từng câu
            ans, ans_type, thinking = solve_question(q, data_dir)

            # Lưu log chi tiết từng câu
            log_data = {
                'id': q_id,
                'thinking': thinking,
                'answer': ans,
                'type': ans_type
            }
            log_path = f'/result/logs/{q_id}.json'
            with open(log_path, 'w', encoding='utf-8') as lf:
                json.dump(log_data, lf, ensure_ascii=False, indent=2)

            # Đưa vào danh sách submission chung
            submissions.append({
                'id': q_id,
                'answer': ans,
                'type': ans_type
            })
            count += 1
            if count % 100 == 0:
                print(f'Đã xử lý xong {count} câu...')

    # Ghi file submission tổng hợp
    with open(output_submission, 'w', encoding='utf-8') as sf:
        for sub in submissions:
            sf.write(json.dumps(sub, ensure_ascii=False) + '\n')

print(f'[predict.sh] Hoàn thành toàn bộ {count} câu trong {time.time() - start_time:.2f} giây!')
"

echo "[predict.sh] Đã xuất file thành công ra /result/"