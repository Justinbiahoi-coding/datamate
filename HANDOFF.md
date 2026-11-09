# HANDOFF — DataMate ZAC 2026 (viết lại 2026-11-10)

Đọc file này trước. Mọi con số dưới đây đã được đo bằng cách chạy lại, không phải ước lượng, trừ chỗ ghi rõ "chưa đo".

## 0. VIỆC CẦN LÀM TIẾP (theo thứ tự ưu tiên)
Dữ liệu train đã sẵn sàng. Còn hạn đến **16/11/2026**, nên ưu tiên huấn luyện và chạy thật, không sa vào cải thiện dữ liệu thêm.

**P0 — bắt buộc, làm theo thứ tự:**
1. **Đọc kết quả kiểm định cuối** `audit_v5_summary.txt` (tự ghi ra khi lượt kiểm tra chạy xong, mất khoảng 17 phút kể từ khi bắt đầu; nếu chưa có file thì chạy `python3 code/audit_strict_all.py`, ghi ra `audit_v5_rerun.json`). Kỳ vọng: 3.000/3.000 trạng thái `ok`. Nếu có id không đạt: giải lại bằng agent (xem `AGENT_PROMPTS.md` mục 3), gộp bằng `code/apply_overlay.py`, tạo lại bộ train.
2. **Kiểm tra `code/train_kaggle.py` trên Kaggle với `MAX_STEPS=5`** (script đã sửa nhưng chưa chạy thử): không OOM ở mẫu 10k token, loss chỉ tính trên phần assistant (`train_on_responses_only`), ghi lại token/giây. Chi tiết ở mục 5.
3. **Train 7B** trên `sft_data_v5_train.jsonl` (2.840 mẫu), rồi **đo accuracy trên 160 câu hold-out** (`holdout_ids.json`) bằng `code/eval_finetune.py`. Chú ý accuracy loại `number` (63% đề).
4. **Làm đường chạy nhanh cho `inference.py`** (vLLM có prefix cache hoặc batch) và đo thời gian 1000 câu; hiện chỉ có `transformers.generate` tuần tự, không đủ trong 6 giờ. Mục 6.
5. Gộp LoRA, `docker build`, test offline với `public_test`, nộp.

**P1 — tuỳ chọn, chỉ khi còn thời gian trong lúc chờ train (mỗi việc dùng agent Sonnet, prompt sẵn ở `AGENT_PROMPTS.md`):**
- **Viết gọn 384 code dài** (> 3.000 ký tự, `batches_compact/`, 20 batch). Lợi ích: chạy thật nhanh hơn, ít lỗi hơn, thống nhất phong cách.
- **Viết lại 228 câu ngày tương đối** (`batches_dates/`, 12 batch) để tính ngày từ `as_of_date`. Lợi ích: model khỏi phải tự nhẩm lịch. Khả năng cao có ích nhất trong hai việc này.
- Sau mỗi việc: `code/apply_overlay.py` (kiểm tra độc lập, rồi gộp), `code/make_sft.py ... --prompt-version v2 --no-dedup`, và tách lại hold-out bằng `holdout_ids.json`. Nếu train đã bắt đầu, **cân nhắc kỹ trước khi đổi dữ liệu**: mọi so sánh accuracy phải dùng cùng tập hold-out.

**Đừng làm:** đừng trộn prompt v1 và v2; đừng dùng `scorer.match_answer` (có dung sai) để quyết định đúng sai (dùng `haiku_check.py` hoặc `apply_overlay.py`); đừng cho agent đọc `_gold_*`; đừng chạy lại `merge_final.py` với file cũ.

**Tái tạo bộ train từ đầu (nếu cần):** `python3 code/build_final5.py` (gộp `sub_final4.jsonl` + `overlay_ok.json` + `sub_haiku/retry11_*`, `retry12_*` + sửa ngày) rồi `python3 code/make_sft.py --from-submission sub_final5.jsonl --out sft_data_v5.jsonl --max-chars 45000 --no-dedup --prompt-version v2`.

## 1. Mục tiêu và hạn
- Bài thi: trả lời câu hỏi tiếng Việt trên dữ liệu bảng doanh nghiệp (CSV/Excel/SQLite), trả về đáp án đúng định dạng (number/percent/date/list/boolean/string/table/unanswerable) hoặc "không trả lời được".
- Cách làm: fine-tune Qwen (<= 15B tham số tổng, LoRA) để **viết code pandas**; chạy code trong sandbox (`code/agent.py: exec_code`) lấy đáp án. Đóng Docker chạy offline trên 2x RTX 5090 (6 giờ cho khoảng 1000 câu private test).
- **Hạn nộp: 16/11/2026 23:59 (GMT+7).** Trọng số phải công khai trước 26/10/2026, giấy phép thoáng.
- Thư mục làm việc: `/Users/buivanthien/Learn/zalo chelen/datamate`.
- Chấm điểm thật: đúng +1, sai -1, bỏ trống 0. **Số và phần trăm khớp tuyệt đối** (tiền đúng từng đồng, số đếm đúng từng đơn vị, phần trăm đúng 2 chữ số thập phân). Không có dung sai ±1%.

## 2. Hai điều quan trọng nhất cần nắm
1. **Bộ test dùng business mới và rulebook khác (dài hơn, thêm luật).** `public_test/rulebook.md` dài 18.8k ký tự (6.022 token) so với `train/rulebook.md` 14.7k (4.745 token), có thêm các luật mới (khách trung thành nhất, giờ cao điểm, ngành mẹ và bé, topping...). Vì vậy model **phải đọc rulebook và README trong prompt**, không thể học thuộc luật theo business. Prompt v1 cũ chỉ đưa 2.000 ký tự đầu của rulebook và 600 ký tự đầu của README; đó là lỗi lớn nhất của bản trước. **Prompt v2 (`code/prompt_v2.py`) đưa đủ cả hai.**
2. **Train và chạy thật phải dùng cùng một prompt.** v2 đã được nối vào `make_sft.py` (`--prompt-version v2`), `agent.infer` (mặc định v2; đặt `DATAMATE_PROMPT=v1` để quay về bản cũ), `eval_finetune.py`, `inference.py`. Không được trộn: dữ liệu v2 mà chạy thật bằng prompt v1 (hoặc ngược lại) sẽ làm model kém hẳn.

## 3. Trạng thái dữ liệu (cuối 2026-11-10)
| Hạng mục | Giá trị |
|---|---|
| **Bộ train cuối** | **`sft_data_v5.jsonl`: 3.000 mẫu** (prompt v2). Đủ 30 business (40–119 mẫu/business). 1.884 `number`, 578 `percent`, 193 `list`, 145 `date`, 88 `string`, 70 `unanswerable`, 23 `boolean`, 19 `table` |
| Chia sẵn để đánh giá | `holdout_ids.json` (160 id, 5+ mỗi business, phân bố tự nhiên: 64% number) và `sft_data_v5_train.jsonl` (2.840 mẫu, đã bỏ 160 id kia). Train trên bản này, đo accuracy trên 160 câu hold-out, sau đó có thể train lại trên đủ 3.000 mẫu |
| Bảng code nguồn | `sub_final5.jsonl` (3.000 dòng, mỗi dòng có `_code`, `answer`, `type`, `_source`) |
| Kiểm định cuối | xem mục 4 |
| Độ dài (đo bằng tokenizer Qwen2.5-Coder thật) | token/mẫu: trung bình 6.959, trung vị 6.712, p95 9.995, p99 10.412, **tối đa 10.715**. Prompt trung bình 6.521 token; câu trả lời (code) trung bình 438, tối đa 1.832. **Tổng 20,9M token mỗi epoch**, trong đó phần tính loss (câu trả lời) chỉ 1,31M (6%). 398 mẫu > 8.192 token, 57 mẫu > 10.240, không mẫu nào > 12.288 |

Nguồn của 3.000 câu: Sonnet (sub agent) ~2.640, Gemini 161, giải lại bằng agent (`resolve11`) 56, viết gọn (`compact12`) 140; sau đó 220 câu được sửa ngày tương đối (`+datefix`).

## 4. Chất lượng dữ liệu: đã làm và chưa làm
**Đã làm (đều kiểm bằng cách chạy lại code trên dữ liệu thật):**
- Mỗi mẫu: code chạy được, khớp gold **tuyệt đối** (kiểm định chặt toàn bộ ở `/tmp/audit_v5.json`, xem kết quả trong mục 9), tự chứa (không `sys.path`, `load_business`, import module phụ, đường dẫn tuyệt đối, `open(`), không hardcode đáp án.
- 601 code từng phụ thuộc file `/tmp/s9_*/h*.py` đã chuyển thành code tự chứa (`sub_selfcontained/`, xem `FIX_SELFCONTAINED.md`).
- 56 câu từng chỉ đúng nhờ dung sai, hoặc dùng hàm đi tắt `cancellation_rate()` / `find_revenue_col()` (mâu thuẫn rulebook) đã được giải lại bằng explicit pandas.
- 140 code quá dài (4–7k ký tự) đã viết gọn trung bình còn 14% độ dài cũ (`sub_haiku/retry12_*`).
- 220 câu có từ tương đối ("hôm nay", "tuần trước", "tháng này", "N ngày gần nhất"...) từng ghi cứng ngày, nay tính từ `as_of_date` (`code/datefix.py`, chỉ sửa khi chắc chắn và kết quả giữ nguyên chính xác).
- `system prompt` cũ (5.7k ký tự) chứa luật viết tay mâu thuẫn rulebook (ví dụ mẫu số tỉ lệ huỷ loại đơn trả). v2 thay bằng bản 1.5k ký tự, không mâu thuẫn.

**Chưa làm / hạn chế đã biết:**
- **~380 code dài (>3.000 ký tự) chưa viết gọn** (`batches_retry12/retry12_007..026`, chưa giao agent). Chúng vẫn đúng và tự chứa nhưng dài, làm chạy thật chậm và lẫn hai phong cách code. Còn ~25% mẫu có code > 1.500 ký tự.
- **~270 câu hỏi dùng từ tương đối vẫn ghi cứng ngày** (bộ chuyển đổi tự động không dám sửa vì không chắc). Model sẽ phải tự tính ngày trong đầu cho các câu dạng này. Nên cho agent viết lại theo `as_of_date` nếu còn thời gian (xem bảng ở `/tmp/resolve_plan.json` đã mất khi tắt máy; tính lại bằng cách quét `sub_final5.jsonl`: câu hỏi có từ tương đối mà `_code` không chứa `as_of_date`).
- "Khớp gold" không chứng minh logic đúng; có thể có code trùng số một cách tình cờ.
- Loại `table` chỉ có 19 mẫu, `boolean` 23 — model sẽ yếu ở hai loại này.
- 750 câu của đợt Antigravity (`retry9`): agent đọc được gold khi giải. Chúng khớp tuyệt đối và không hardcode, nhưng có thể đã được chỉnh theo con số.
- Không có cách nào kiểm tra dữ liệu có làm model tốt hơn ngoài việc train rồi đo accuracy trên hold-out.

## 5. Việc tiếp theo: huấn luyện (Việc C)
`code/train_kaggle.py` **đã được sửa (2026-11-10) nhưng CHƯA chạy thử** (cần GPU, unsloth, TRL; không chạy được trên máy này). Bản cũ lưu ở `code/train_kaggle.v1.bak`. Những gì đã đổi và lý do:
- **Loss chỉ trên phần assistant** (`train_on_responses_only`, marker ChatML `<|im_start|>user\n` / `<|im_start|>assistant\n`). Bản cũ tính loss trên toàn văn bản; vì 94% token mỗi mẫu là prompt (rulebook, README, danh sách biến), model sẽ tốn gần hết sức học để thuộc prompt. Nếu phiên bản TRL/unsloth trên Kaggle không có hàm này hoặc báo lỗi, cần cách khác để che loss ở phần prompt; không nên train nếu loss còn tính trên prompt.
- **`packing=False`** (mẫu dài 7–10k token; packing không có lợi, lại trộn các mẫu vào nhau).
- **`MAX_SEQ_LEN` mặc định 11264** (mẫu dài nhất 10.715 token; thấp hơn sẽ cắt mất câu hỏi/code). Script có `assert` dừng lại nếu còn mẫu dài hơn `MAX_SEQ_LEN`, tránh cắt âm thầm.
- `BATCH_SIZE=1`, `GRAD_ACCUM=16`, `EPOCHS=2`, `VAL_RATIO=0.03` (độ chính xác đo trên `holdout_ids.json`, không phải val loss), `SFT_DATA_PATH` mặc định `sft_data_v5_train.jsonl`.
- Còn lại giữ nguyên: `MODEL_NAME=Qwen/Qwen2.5-Coder-7B-Instruct`, LoRA rank 32 mọi lớp tuyến tính, LR 2e-4 cosine, warmup 3%, lưu checkpoint tốt nhất theo val loss.

**Việc cần làm:**
- Upload `sft_data_v5_train.jsonl` làm dataset Kaggle `datamate-sft`.
- **Chạy thử vài bước trước** (đặt `MAX_STEPS=5`): xác nhận không OOM ở mẫu 10k token, `train_on_responses_only` chạy được, ghi lại token/giây để ước lượng thời gian. Tính: 2 epoch x 20,9M token. Nếu tốc độ chỉ ~1.500 token/giây thì 1 epoch mất khoảng 3,9 giờ; cân nhắc 1 epoch, hoặc GPU mạnh hơn (A100/H100), vì Kaggle T4 không có FlashAttention.
- Sau khi train: `code/eval_finetune.py` trên các id trong `holdout_ids.json` (dùng prompt v2, đã nới giới hạn token), xem accuracy theo loại, đặc biệt `number` (63% đề). Nếu ổn, train lại trên đủ `sft_data_v5.jsonl`.
- Bắt đầu với 7B (14B từng quá chậm: 200 giây/câu). Tổng tham số phải <= 15B.

## 6. Việc D: đóng gói và nộp
- `Dockerfile` (CUDA 12.8, Python 3.11, offline: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `DATAMATE_LLM_BACKEND=local`), `predict.sh`, `code/inference.py` (log từng câu, có resume).
- **Tốc độ là rủi ro lớn:** `agent.call_llm` dùng `transformers.generate` tuần tự, không batch. Với prompt khoảng 7–12k token và code trả lời trung bình 438 token (tối đa 1.832), 1000 câu trong 6 giờ chỉ khả thi nếu dùng vLLM (có prefix cache cho phần rulebook dùng chung) hoặc batch. Hiện chưa có đường vLLM trong `inference.py`. Cần làm và đo trước khi nộp.
- `max_new_tokens=1200` trong `inference.py`/`eval_finetune.py` thấp hơn câu trả lời dài nhất (1.832 token); nâng lên khoảng 2.048.
- Prompt chạy thật là v2 (mặc định trong `agent.infer`). Rulebook lấy từ `/data/rulebook.md` của bộ test (dài hơn bộ train); `inference.py` đã nới giới hạn token đầu vào lên 20.000.
- Cơ chế thử lại khi code lỗi (`agent.infer`) chưa từng được huấn luyện (model chưa thấy định dạng "Error: ... Fix the code."), nên chất lượng lần thử lại chưa đo.
- Kiểm tra: không gọi mạng, tổng tham số <= 15B, đủ 1000 câu trong 6 giờ, ghi log `/result/logs/`.
- Lệnh chi tiết: `PIPELINE.md` (một phần đã cũ, ưu tiên file này).

## 7. File nào dùng, file nào bỏ qua
**Dùng:**
- `sft_data_v5.jsonl`, `sft_data_v5_train.jsonl`, `holdout_ids.json` — dữ liệu train và tập đánh giá.
- `sub_final5.jsonl` — bảng code cuối (nguồn của bộ train).
- `code/prompt_v2.py` — prompt dùng chung cho train và chạy thật. `code/datefix.py` — sửa ngày tương đối. `code/verify_selfcontained.py` — kiểm tra tự chứa. `code/haiku_check.py` — chấm một lời giải (đã **chấm chặt**).
- `code/make_sft.py` (có `--prompt-version v2`, `--no-dedup`, `--max-chars`), `merge_final.py`, `agent.py`, `loader.py`, `scorer.py`, `train_kaggle.py`, `eval_finetune.py`, `inference.py`.
- `train/rulebook.md`, `public_test/rulebook.md`, và `README.md` trong từng thư mục dữ liệu.
- `sub_haiku/*.jsonl` (đáp án đã kiểm của từng đợt agent, mỗi batch một file, đã bị gộp vào `sub_final5.jsonl`), `batches_retry*/` (câu hỏi giao agent), `backup_s9/` (sao lưu các file phụ `/tmp/s9_*`).

**Bỏ qua:**
- `sft_data.jsonl`, `sft_data_v2/v3/v4.jsonl`, `sub_final.jsonl`, `sub_final2/3/4.jsonl`, `sub_sonnet*.jsonl` và các `*.bak*` — bản cũ. **Không chạy lại `merge_final.py` với các file này**: script lấy dòng cuối của mỗi id, dòng rác có thể ghi đè câu đúng.
- Các file rác do sub agent tạo ở thư mục gốc (`q_*.py`, `batch_*.py`, `process_*.py`, `*_status.md`, `BATCH*_PROCESSING.md`, `QUICK_START_*.sh`...). Có thể xoá sau khi sao lưu.
- `code/selfgen.py`, `code/adapters.py`, `code/_h.py` — do OpenCode viết (hướng tự sinh code offline), chưa kiểm chứng.

## 8. Bài học khi giao việc cho sub agent (nếu cần giải thêm hoặc viết gọn)
1. **Dùng model Sonnet** (`model: "sonnet"` khi tạo agent). Haiku rất kém: 10 agent chạy 10 phút ra 8 câu đúng.
2. **Không giao qua `code/agent.py`** (cần backend LLM ngoài). Agent phải tự viết code pandas. Không cần API key nào; biến môi trường ở shell chính không truyền sang agent.
3. Mỗi agent 1 batch 13–25 câu; tạo agent từng cái một (tạo cả loạt song song có thể báo `Lock file is already being held`); khoảng 10 agent mỗi đợt.
4. **Cấm agent đọc `_gold_*`; chỉ dùng kết quả CORRECT/WRONG của `haiku_check.py`.** Cấm dùng `cancellation_rate()` / `find_revenue_col()`.
5. **Code phải tự chứa** (chỉ pandas/numpy/re/unicodedata/math/datetime/decimal; dữ liệu lấy từ các biến mà `exec_code` cấp sẵn). Kiểm bằng `code/verify_selfcontained.py`.
6. **Luôn chấm chặt** (`haiku_check.py` nay chấm tuyệt đối). Scorer cũ (`scorer.match_answer`) có dung sai ±1% nên để lọt lời giải sai ngữ nghĩa (ví dụ code 'hôm qua' dùng cho câu 'hôm nay': 114 so với 113).
7. Khi kiểm định lại code, **nạp dữ liệu riêng cho từng câu** (nhiều code sửa DataFrame tại chỗ; dùng chung dữ liệu làm báo sai giả). Khi viết code, dùng `.copy()` trước khi sửa.
8. Python `round()` làm tròn nửa-về-chẵn; rulebook yêu cầu làm tròn nửa lên cho tiền trung bình: dùng `decimal.ROUND_HALF_UP` hoặc `math.floor(x+0.5)`.
9. Lỗi dữ liệu hay gặp: doanh thu = tổng thành tiền các dòng hàng (không phải tổng hoá đơn), tên sản phẩm lệch hoa/thường/dấu/khoảng trắng, `vn_normalize` không đổi `đ` thành `d`, chuỗi tiền `1tr440`/`45k`/`45.000đ`, trạng thái huỷ/trả khác nhau theo business, dòng trùng hệt của cùng một đơn (tính một lần), ô trống cần điền xuống, khách lẻ nhiều biến thể.
10. Gold có thể kèm `alias` (ví dụ `NV002` với alias là tên người); đáp án khớp alias là hợp lệ.

## 9. Kết quả kiểm định cuối
Lượt kiểm tra chặt cuối (chạy lại từng `_code` của `sub_final5.jsonl` với dữ liệu nạp riêng cho từng câu, so khớp tuyệt đối với gold) tự ghi kết quả vào **`audit_v5_summary.txt`** (tóm tắt) và `audit_v5.json` (chi tiết từng câu) trong thư mục này khi chạy xong. Nếu thiếu hai file đó, chạy lại: `python3 code/audit_strict_all.py` (mất khoảng 17 phút, ghi `audit_v5_rerun.json`). Các kiểm định trước đó (đều chạy lại thật): `sub_final4` 2.977/3.000 khớp chặt, 23 chỉ đúng nhờ dung sai (nay đã giải lại); 196 code mới (56 giải lại + 140 viết gọn) khớp chặt 196/196; chuyển ngày: 220 câu, kết quả giữ nguyên 100%.
**Kiểm tra khớp train/chạy thật (12 mẫu ngẫu nhiên):** prompt mà `agent.infer` gửi cho model trùng từng ký tự với prompt trong `sft_data_v5.jsonl` (12/12).

## 10. Rủi ro và lưu ý
- Một khoá Gemini đã bị dán vào cuộc trò chuyện. Nên thu hồi/đổi ở Google AI Studio; không ghi khoá vào file nào.
- Thư mục gốc rất lộn xộn; chỉ dọn sau khi đã sao lưu `sub_haiku/`, `sub_final5.jsonl`, `sft_data_v5*.jsonl`.
- Cần bật auto mode (Shift+Tab) và có rule `python3 code/*`, `python3 -c *` để sub agent khỏi bị hỏi quyền.
- Số liệu token đo bằng `tokenizers` + `tokenizer.json` của `Qwen/Qwen2.5-Coder-7B-Instruct` (cài trong một venv tạm). Qwen3 hoặc model khác có thể đếm khác một chút.

## 11. Checklist
- [x] Giải đủ 3.000 câu, tự chứa, chấm chặt
- [x] Sửa prompt (v2) và nối vào make_sft / agent.infer / eval_finetune / inference
- [x] Giải lại 56 câu, viết gọn 140 code, sửa ngày tương đối 220 câu
- [x] Tạo `sft_data_v5.jsonl`, tách hold-out, đo token thật
- [x] Sửa `train_kaggle.py` (loss chỉ trên assistant, không packing, `MAX_SEQ_LEN=11264`) — **chưa chạy thử**
- [ ] Chạy thử `MAX_STEPS=5` trên Kaggle: không OOM, loss chỉ trên assistant hoạt động, đo token/giây
- [ ] Train 7B trên `sft_data_v5_train.jsonl`, đo accuracy trên `holdout_ids.json` bằng `eval_finetune.py`
- [ ] Thêm đường chạy nhanh (vLLM/batch) cho `inference.py`, đo thời gian 1000 câu
- [ ] (Tuỳ chọn) viết gọn ~380 code dài còn lại; sửa ~270 câu ngày tương đối còn lại
- [ ] Gộp LoRA, `docker build`, test offline với `public_test`
- [ ] Nộp trước 16/11/2026 23:59 (GMT+7)
