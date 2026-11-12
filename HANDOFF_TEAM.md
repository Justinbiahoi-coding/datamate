# Bàn giao DataMate (ZAC 2026) — trạng thái 12/11/2026 sáng

Hạn nộp Docker: **16/11/2026 23:59 (GMT+7)**. File này đủ để người mới tiếp tục mà không cần hỏi lại. Đọc mục 1–3 trước, các mục sau là tra cứu.

## 1. Tóm tắt 1 phút

- Cách làm: model **Qwen2.5-Coder-7B-Instruct + LoRA** (QLoRA, rank 32) đọc câu hỏi + rulebook + mô tả dữ liệu, **viết code pandas**, chạy code, lấy `RESULT`. Lúc chạy thật: sinh nhiều bản code, **bỏ phiếu**, chỉ trả lời khi các bản đồng ý, còn lại **abstain** (chấm điểm: đúng +1, sai −1, abstain 0).
- Model hiện tại **còn yếu**: trên 10 câu hold-out đúng 2/10; trên public test (adapter s3 cũ) chỉ 81/432 câu chạy được code. Không kỳ vọng lên top; mục tiêu thực tế là **bài nộp hợp lệ, điểm ≥ 0**.
- Việc dở dang: **phiên train t2** (đang ở checkpoint-10/90) và **chưa từng chạy thử đường suy luận vLLM trên GPU** (đây là thứ Docker sẽ dùng). Docker image **chưa build**.

## 2. Việc cần làm tiếp (theo thứ tự ưu tiên)

1. **Chạy tiếp train t2 trên Colab** (mục 5). Khoảng 8 giờ trên T4. Kết quả: adapter `final_lora` cho prompt v3.
2. **Kiểm thử suy luận vLLM trên GPU** với adapter tốt nhất (t2 nếu xong, không thì t1) trên các câu hold-out có đáp án (mục 6): đo độ đúng, tốc độ, và **chỉnh ngưỡng bỏ phiếu** `VOTE_MIN_AGREE`/`VOTE_MIN_SHARE` sao cho điểm (đúng − sai) cao nhất.
3. **Build Docker** đúng hướng dẫn chính thức (mục 7), chạy thử offline.
4. **Chạy public test và nộp lên leaderboard** để có điểm tham chiếu (tối đa 5 lần/ngày).
5. **Kiểm tra tái lập**: chạy 2 lần, chênh lệch điểm phải ≤ 0,03.

Nếu thiếu thời gian: bỏ bước 1, dùng adapter t1 cho bước 2–5. Docker hợp lệ quan trọng hơn train thêm.

## 3. Trạng thái các lần train

Tất cả: base `unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit`, LoRA r=32 trên q/k/v/o/gate/up/down, batch 1 × grad-accum 16, loss chỉ trên phần trả lời (code), T4.

| Phiên | Dữ liệu | Prompt | Kết quả |
|---|---|---|---|
| p1 | 1.552 mẫu (code cũ) | v2 | eval_loss 0,298 |
| p2 | 1.204 mẫu còn lại (code cũ) | v2 | eval_loss 0,126 (hết epoch 1) |
| s3 | nửa A, 84/92 bước (code cũ) | v2 | probe: câu đã train 2/5, hold-out 1/10 (4/10 code chạy được) |
| t1 | nửa B, **code chuẩn hóa**, 65/90 bước | **v3** | probe: 2/5, hold-out 2/10 (**9/10** code chạy được) |
| **t2** | nửa A, code chuẩn hóa | v3 | **dở dang: checkpoint-10/90**, loss bước 5/10: 0,274 / 0,262 |

**Quan trọng:** adapter phải chạy với đúng phiên bản prompt đã dùng lúc train: s3 → `DATAMATE_PROMPT=v2`; t1, t2 → `DATAMATE_PROMPT=v3`.

Probe = 5 câu đã train + 10 câu hold-out đầu tiên, sinh 1 lần (greedy), chấm đúng tuyệt đối. Mẫu nhỏ, chỉ để thấy xu hướng.

**Chẩn đoán (đã đo):** pipeline chấm/prompt/nạp adapter đúng (kiểm bằng code mẫu: 160/160 đúng; prompt khớp lúc train 40/40). Model yếu vì học ít (≈2 epoch, T4 chậm: 1 epoch ≈ 19 giờ) và dữ liệu cũ thiếu nhất quán (154 tên hàm phụ khác nhau) — đã sửa bằng chuẩn hóa code (bộ v7). Public test dùng **14 doanh nghiệp không có trong train** và **rulebook có thêm quy tắc mới**, nên khó hơn hold-out.

**Public test với adapter s3** (11,2 giờ trên Kaggle T4, chỉ kịp 432/1.000 câu): 81 câu code chạy được; lỗi chính: 76 câu cùng doanh nghiệp `dev_003` gọi nhầm cột `'Ngày áp dụng'` của sheet lịch sử giá; 54 câu code quá dài bị lệch ngoặc. Hai file nộp đã tạo (`submissions/submission_A_answer_all.jsonl` 81 câu trả lời, `submission_B_filtered.jsonl` 59 câu, bỏ kết quả 0/NaN/rỗng) — **chưa có điểm**.

## 4. Dữ liệu và file

| File | Ý nghĩa |
|---|---|
| `holdout_ids.json` | 160 câu train giữ lại để đo, **không bao giờ train** |
| `sub_final6.jsonl` | bảng code đã kiểm định cho 3.000 câu (kiểu cũ) |
| `sub_final7.jsonl` | bảng code **chuẩn hóa** (1.609 câu viết lại, 32 câu giữ code cũ vì mất logic ngày) — dùng file này |
| `sft_data_v7.jsonl` | dữ liệu train (prompt v3, code chuẩn hóa), 3.000 dòng; train = các dòng **không** thuộc hold-out (2.840) |
| `colab_t2/sft_t2.jsonl` | nửa A của v7 (1.469 dòng) cho phiên t2 |
| `CANON_CODE_GUIDE.md` | quy chuẩn viết code mẫu + quy trình agent viết lại |

`train/`, `infor/` (dữ liệu BTC) **không có trong git** — lấy từ trang thi và đặt đúng chỗ: `train/`, `infor/data/public_test/`.

Dựng lại dữ liệu train:
```
python3 code/make_sft.py --from-submission sub_final7.jsonl --out sft_data_v7.jsonl --max-chars 45000 --no-dedup --prompt-version v3
```
Kiểm định một bảng code (chạy lại mọi code, so đúng tuyệt đối với đáp án): `code/apply_overlay.py` (xem docstring).

## 5. Train (script `code/train_kaggle.py`)

Cấu hình qua biến môi trường:

| Biến | Ý nghĩa |
|---|---|
| `SFT_DATA_PATH` | file jsonl dữ liệu |
| `OUTPUT_DIR` | nơi lưu checkpoint và `final_lora/` |
| `INIT_ADAPTER` | adapter khởi động (thư mục có `adapter_model.safetensors`) |
| `RESUME_CKPT` | checkpoint để chạy tiếp (khôi phục cả optimizer và lịch LR) |
| `LR`, `EPOCHS`, `MAX_STEPS` | t1: 1e-4; t2: 7e-5; 1 epoch |
| `SAVE_STEPS`, `EVAL_STEPS` | `EVAL_STEPS=0` tắt đánh giá (tiết kiệm GPU) |
| `TIME_LIMIT_H` | tự dừng và lưu khi quá số giờ (Kaggle cắt ở 12 giờ) |
| `MAX_SEQ_LEN` | 12288 cho prompt v3 (script dừng nếu có mẫu bị cắt) |

Log đầu phải thấy: `[INIT] ... unexpected_keys=0`, `[LEN] ... : 0`, `[DATA] train=1425`, `[MASK] ...(≈1–4%)`, và nếu chạy tiếp thì `[RESUME] from ...`.

### Chạy tiếp t2 trên Colab (cách dễ nhất)
1. Lấy thư mục `colab_t2/` (Thiên chia sẻ qua Google Drive; 809 MB): `run_colab_t2.ipynb`, `train_kaggle.py`, `sft_t2.jsonl`, `t1_lora/`, `out/checkpoint-10/`.
2. Đặt vào **My Drive** đúng đường dẫn `MyDrive/colab_t2`.
3. Mở notebook bằng Colab, chọn **T4 GPU**, chạy lần lượt các ô (ô 2 hỏi quyền Drive → cho phép). Ô cuối tự chạy tiếp từ checkpoint mới nhất trong `MyDrive/colab_t2/out/`.
4. **Giữ tab mở** (Colab miễn phí ngắt khi bỏ không). Bị ngắt thì mở lại, chạy lại từ ô 1. Checkpoint lưu vào Drive mỗi 10 bước (~1 giờ).
5. Xong: `MyDrive/colab_t2/out/final_lora/` là adapter t2. Tốc độ T4 ≈ 370 giây/bước, còn 80 bước ≈ 8,3 giờ.

## 6. Suy luận (`code/inference.py`)

```
DATAMATE_PROMPT=v3 VLLM_DTYPE=half VLLM_TP=2 \
python3 code/inference.py --data-root <split_root> --out out/submission.jsonl --logs out/logs \
  --model Qwen/Qwen2.5-Coder-7B-Instruct --lora <adapter_dir> --backend vllm
```
- `<split_root>` chứa `questions.jsonl`, `rulebook.md`, `data/`, `calendar.csv`.
- `VLLM_DTYPE=half` cho T4 (không có bf16); trên RTX 5090 để mặc định `auto`. `VLLM_TP=2` chia model qua 2 GPU.
- Bỏ phiếu: `VOTE_K` (5 bản: 1 greedy + 4 lấy mẫu), `VOTE_MIN_AGREE` (2), `VOTE_MIN_SHARE` (0,4), `VOTE_REPAIRS` (2 lần hỏi lại kèm tên cột thật). **Ngưỡng chưa hiệu chỉnh** — hiệu chỉnh trên hold-out: tạo thư mục tạm (ví dụ `holdout_split/`) có `questions.jsonl` chỉ gồm 160 câu trong `holdout_ids.json`, còn `data/`, `rulebook.md`, `calendar.csv` là symlink tới `train/`; chạy `inference.py --data-root holdout_split`, rồi so với `train/answers.jsonl`. Log mỗi câu có `votes.cands` để chỉnh ngưỡng không cần chạy lại GPU.
- Kiểm tra logic bỏ phiếu không cần GPU: `python3 code/test_voting.py`.
- Định dạng nộp: mỗi dòng `{"id","type","answer"}`; **percent là số** (`2.08`, không phải `"2.08%"` — đã tự đổi trong `to_submission`); câu không chắc `{"type":"abstain","answer":null}`.
- Log theo yêu cầu BTC (`/result/logs/<id>.json`): `id`, `answer{type,answer}`, `elapsed_ms`, `thinking` (null), `code`, `output`.

**Chưa kiểm chứng:** đường vLLM chưa chạy trên GPU lần nào. Cách sinh theo lô bằng transformers/unsloth trên T4 rất chậm (100–240 giây/câu) — đừng dùng cho 1.000 câu.

## 7. Docker (theo `infor/submission guild/zac2026_DataMate_docker_guideline_final.pdf`)

- Base `vllm/vllm-openai:v0.10.1.1`, `ENTRYPOINT []`, `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 NCCL_P2P_DISABLE=1`, cài thêm `nvidia-nccl-cu12==2.27.7`.
- Bố cục `/code/`: `predict.sh` (không tham số, đọc `/data`, ghi `/result/submission.jsonl` và `/result/logs/`), `README.md`, `requirements.txt`, `src/`, `models/` (base model + adapter, hoặc model đã gộp), `training_code/` (code train, dữ liệu train/val, log, `data_manifest.json` có SHA-256).
- `predict.sh` phải đặt cố định model, seed, nhiệt độ, `DATAMATE_PROMPT` đúng với adapter.
- Lệnh chấm của BTC: `docker run --rm --gpus '"device=0,1"' --network none --shm-size=16g --entrypoint bash -v <test>:/data:ro -v <out>:/result <image> /code/predict.sh`. Giới hạn **6 giờ**, image ≤ 100 GB, tên `zaic2026_datamate_<team>:final`.
- README phải khai báo: model (nguồn, revision, giấy phép, số tham số ≤ 15B), dữ liệu tự sinh (code mẫu được sinh bằng các LLM rồi kiểm định đúng tuyệt đối; lưu prompt/batch trong repo: `AGENT_PROMPTS.md`, `CANON_CODE_GUIDE.md`, `batches_*`), số mẫu train/val. **Không được train trên dữ liệu test.**
- `Dockerfile`/`predict.sh` hiện có trong repo là bản cũ (base CUDA, đường dẫn `/app`) — phải viết lại theo các điểm trên.

## 8. Bài học đã trả giá

- Kaggle: trạng thái CLI báo trễ; kernel có thể xếp hàng hàng giờ; phiên cắt cứng ở 12 giờ; quota GPU 30 giờ/tuần/tài khoản; tài khoản chưa xác minh số điện thoại **không có GPU và internet** (kernel chạy CPU, không báo lỗi ngay).
- Colab qua CLI: mỗi lệnh giữ phiên sống tối đa ~2 giờ phía máy local; máy bị thu hồi khi kernel rảnh → mất checkpoint trên ổ máy. Gắn Drive qua CLI không ổn định. Dùng notebook trên trình duyệt + Drive.
- `eval_loss` thấp **không** có nghĩa là trả lời đúng; luôn đo bằng chạy code thật (probe/hold-out).
- Không dùng `git checkout/restore/stash` khi có người khác đang sửa file trong repo (đã mất một lần thay đổi chưa commit).
