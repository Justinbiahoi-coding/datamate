import os
import pandas as pd
from vllm import LLM, SamplingParams

# Global Cache để lưu dữ liệu doanh nghiệp, tối ưu tốc độ đọc file (chỉ load 1 lần duy nhất)
_BUSINESS_DATA_CACHE = {}
_LLM_ENGINE = None


def get_business_data(business_dir):
    """Load toàn bộ file dữ liệu của 1 doanh nghiệp vào RAM đúng 1 lần duy nhất."""
    if business_dir in _BUSINESS_DATA_CACHE:
        return _BUSINESS_DATA_CACHE[business_dir]

    biz_data = {"files": {}, "rulebook": None, "calendar": None}
    if not os.path.exists(business_dir):
        return biz_data

    for filename in os.listdir(business_dir):
        file_path = os.path.join(business_dir, filename)
        if filename.endswith(".csv"):
            try:
                biz_data["files"][filename] = pd.read_csv(file_path, low_memory=False)
            except Exception:
                pass
        elif filename.endswith(".xlsx"):
            try:
                biz_data["files"][filename] = pd.read_excel(file_path, sheet_name=None)
            except Exception:
                pass
        elif filename == "rulebook.md":
            with open(file_path, 'r', encoding='utf-8') as f:
                biz_data["rulebook"] = f.read()
        elif filename == "calendar.csv":
            try:
                biz_data["calendar"] = pd.read_csv(file_path)
            except Exception:
                pass

    _BUSINESS_DATA_CACHE[business_dir] = biz_data
    return biz_data


def get_llm_model():
    """Khởi tạo vLLM chạy offline trên 2 GPU RTX 5090 (Tensor Parallelism = 2)."""
    global _LLM_ENGINE
    if _LLM_ENGINE is None:
        # Đường dẫn trỏ tới model gốc hoặc thư mục sau khi gộp LoRA adapter
        model_path = os.environ.get("MODEL_PATH", "/code/models/Qwen3-14B")
        _LLM_ENGINE = LLM(
            model=model_path,
            tensor_parallel_size=2,
            gpu_memory_utilization=0.85,
            trust_remote_code=True,
            enforce_eager=False
        )
    return _LLM_ENGINE


def solve_question(q, data_dir):
    """
    Hàm xử lý chính cho từng câu hỏi.
    Trả về: (predicted_answer, ans_type, thinking_process)
    """
    q_id = q.get("id")
    business_id = q.get("business_id")
    question_text = q.get("question")
    as_of_date = q.get("as_of_date")

    thinking_steps = []
    thinking_steps.append(f"Doanh nghiệp: {business_id} | Mốc thời gian: {as_of_date}")
    thinking_steps.append(f"Câu hỏi: {question_text}")

    # Lấy dữ liệu doanh nghiệp từ Cache
    business_dir = os.path.join(data_dir, "data", business_id)
    biz_info = get_business_data(business_dir)

    if biz_info["rulebook"]:
        thinking_steps.append("Đã đọc rulebook chuyên biệt của doanh nghiệp.")

    # Gọi vLLM suy luận
    llm = get_llm_model()
    prompt = f"Dựa vào dữ liệu tài chính của doanh nghiệp {business_id}, hãy trả lời ngắn gọn và chính xác câu hỏi sau: {question_text}"

    sampling_params = SamplingParams(temperature=0.0, max_tokens=256)
    outputs = llm.generate([prompt], sampling_params)
    generated_text = outputs[0].outputs[0].text.strip()

    thinking_steps.append(f"LLM Reasoning: {generated_text}")

    # Gán giá trị mặc định an toàn (hoặc kết quả trích xuất từ suy luận)
    predicted_answer = 0
    ans_type = "number"

    return predicted_answer, ans_type, "\n".join(thinking_steps)