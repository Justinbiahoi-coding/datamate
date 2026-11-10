import os
import json
import time
from utils import get_root_rulebook
from engine import solve_question
from tqdm import tqdm

# Tự động nhận diện môi trường Docker (/data) hay Local
if os.path.exists("/data"):
    DATA_DIR = "/data"
else:
    DATA_DIR = r"D:\Quang Tran\PyCharm_Data\Zalo_AI_Private\public_test"

QUESTIONS_FILE = os.path.join(DATA_DIR, "questions.jsonl")
RESULT_DIR = "/result" if os.path.exists("/result") else "./output"

def main():
    start_time = time.time()
    print("--- Bắt đầu quá trình suy luận (Prediction) ---")

    # Tạo thư mục output và logs nếu chưa có
    os.makedirs(RESULT_DIR, exist_ok=True)
    logs_dir = os.path.join(RESULT_DIR, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # 1. Nạp rulebook chung
    rulebook_content = get_root_rulebook(DATA_DIR)
    print(f"Đã nạp rulebook chung (Độ dài: {len(rulebook_content)} ký tự)")

    # 2. Đọc danh sách câu hỏi từ questions.jsonl
    if not os.path.exists(QUESTIONS_FILE):
        print(f"[LỖI] Không tìm thấy file questions.jsonl tại {QUESTIONS_FILE}")
        return

    questions = []
    with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))

    print(f"Tổng số câu hỏi cần xử lý: {len(questions)}")

    submission_file_path = os.path.join(RESULT_DIR, "submission.jsonl")

    # 3. Duyệt qua từng câu hỏi với tqdm và gọi engine xử lý
    with open(submission_file_path, 'w', encoding='utf-8') as sub_f:
        for q in tqdm(questions, desc="Đang xử lý task"):
            q_id = q.get("id")
            start_q_time = time.time()

            # Gọi bộ não engine.py để giải quyết câu hỏi
            predicted_answer, ans_type, thinking_process = solve_question(q, DATA_DIR)

            elapsed_ms = int((time.time() - start_q_time) * 1000)

            # Ghi kết quả vào submission.jsonl (Mỗi dòng 1 JSON object theo chuẩn Zalo AI)
            sub_record = {
                "id": q_id,
                "type": ans_type,
                "answer": predicted_answer
            }
            sub_f.write(json.dumps(sub_record, ensure_ascii=False) + "\n")
            sub_f.flush()  # Ép ghi dữ liệu thẳng xuống ổ cứng, không sợ mất data khi ngắt giữa chừng

            # Ghi log chi tiết vào thư mục /result/logs/[id].json
            log_record = {
                "id": q_id,
                "answer": predicted_answer,
                "elapsed_ms": elapsed_ms,
                "thinking": thinking_process,
                "code": None,
                "output": predicted_answer
            }
            log_file_path = os.path.join(logs_dir, f"{q_id}.json")
            with open(log_file_path, 'w', encoding='utf-8') as log_f:
                json.dump(log_record, log_f, ensure_ascii=False, indent=2)

    total_time = time.time() - start_time
    print(f"\n[OK] Hoàn thành toàn bộ pipeline trong {total_time:.2f} giây!")
    print(f"Kết quả được lưu tại: {submission_file_path}")

if __name__ == "__main__":
    main()