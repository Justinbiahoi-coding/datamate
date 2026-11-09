"""QLoRA fine-tuning for DataMate on Kaggle T4/P100.

Upgrades vs v1:
  - Train/val split 90/10 (technique #9: early stop on val)
  - v5: no packing, loss on the assistant reply only (train_on_responses_only), MAX_SEQ_LEN 11264
  - LoRA rank 32 on all linear layers (technique #7)
  - Cosine LR, 3% warmup (technique #8)
  - Save best checkpoint by val_loss
  - Config qua ENV để chia session (14B needs resume_from_checkpoint)

Env overrides:
  MODEL_NAME       default Qwen/Qwen2.5-Coder-7B-Instruct, set to -14B for bigger
  SFT_DATA_PATH    default /kaggle/input/datamate-sft/sft_data_v5_train.jsonl
  OUTPUT_DIR       default /kaggle/working/lora_out
  MAX_STEPS        overrides EPOCHS for session-based training (resume)
  RESUME_CKPT      path to checkpoint to resume from
  EPOCHS           default 2
  LORA_RANK        default 32
  LR               default 2e-4 (7B), use 1e-4 for 14B
"""
import os

MODEL_NAME      = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-Coder-7B-Instruct")
SFT_DATA_PATH   = os.environ.get("SFT_DATA_PATH", "/kaggle/input/datamate-sft/sft_data_v5_train.jsonl")
OUTPUT_DIR      = os.environ.get("OUTPUT_DIR", "/kaggle/working/lora_out")
MAX_SEQ_LEN     = int(os.environ.get("MAX_SEQ_LEN", "11264"))   # longest v5 sample = 10715 tokens; shorter would truncate the question/code
LORA_RANK       = int(os.environ.get("LORA_RANK", "32"))
EPOCHS          = int(os.environ.get("EPOCHS", "2"))             # v5 = ~21M tokens/epoch
BATCH_SIZE      = int(os.environ.get("BATCH_SIZE", "1"))         # samples are 7-10k tokens
GRAD_ACCUM      = int(os.environ.get("GRAD_ACCUM", "16"))
LR              = float(os.environ.get("LR", "2e-4"))
MAX_STEPS       = int(os.environ.get("MAX_STEPS", "-1"))  # -1 = use EPOCHS
RESUME_CKPT     = os.environ.get("RESUME_CKPT", "")
VAL_RATIO       = float(os.environ.get("VAL_RATIO", "0.03"))     # accuracy is measured on holdout_ids.json, not here
SEED            = int(os.environ.get("SEED", "42"))

print(f"[CONFIG] model={MODEL_NAME}  rank={LORA_RANK}  lr={LR}  "
      f"bs={BATCH_SIZE}×{GRAD_ACCUM}={BATCH_SIZE*GRAD_ACCUM}eff  "
      f"epochs={EPOCHS}  max_steps={MAX_STEPS}  val_ratio={VAL_RATIO}")

# ── Setup model ──────────────────────────────────────────────────────────────

from unsloth import FastLanguageModel
import torch

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_NAME,
    max_seq_length=MAX_SEQ_LEN,
    dtype=None,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=LORA_RANK,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_alpha=LORA_RANK,   # alpha = rank (standard QLoRA)
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=SEED,
)

# ── Dataset: train/val split ──────────────────────────────────────────────────

import json
import random
from datasets import Dataset

records = []
with open(SFT_DATA_PATH, encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        text = tokenizer.apply_chat_template(
            item["messages"], tokenize=False, add_generation_prompt=False,
        )
        records.append({"text": text, "gold_type": item.get("gold_type", "unknown")})

# Never truncate silently: a cut sample loses its question/code.
lens = [len(tokenizer(r["text"]).input_ids) for r in records]
too_long = sum(l > MAX_SEQ_LEN for l in lens)
print(f"[LEN] tokens/sample mean={sum(lens)/len(lens):.0f} max={max(lens)} > MAX_SEQ_LEN({MAX_SEQ_LEN}): {too_long}")
assert too_long == 0, "raise MAX_SEQ_LEN or drop long samples; truncating would cut the question/code"

random.Random(SEED).shuffle(records)
n_val = max(int(len(records) * VAL_RATIO), 20)
val_records = records[:n_val]
train_records = records[n_val:]

train_ds = Dataset.from_list(train_records)
val_ds   = Dataset.from_list(val_records)
print(f"[DATA] train={len(train_ds)}  val={len(val_ds)}")

# ── Trainer ──────────────────────────────────────────────────────────────────

import inspect
from trl import SFTTrainer, SFTConfig

_sig = inspect.signature(SFTConfig.__init__).parameters
_kw = dict(
    per_device_train_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRAD_ACCUM,
    num_train_epochs=EPOCHS if MAX_STEPS < 0 else 1,
    max_steps=MAX_STEPS,                        # -1 = no cap
    learning_rate=LR,
    fp16=not torch.cuda.is_bf16_supported(),
    bf16=torch.cuda.is_bf16_supported(),
    logging_steps=int(os.environ.get("LOG_STEPS", "10")),
    output_dir=OUTPUT_DIR,
    save_strategy="steps",
    save_steps=int(os.environ.get("SAVE_STEPS", "40")),
    save_total_limit=3,
    eval_strategy="steps",                      # eval on val set
    eval_steps=int(os.environ.get("SAVE_STEPS", "40")),
    load_best_model_at_end=True,                # keep best val checkpoint
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    optim="adamw_8bit",
    lr_scheduler_type="cosine",                 # technique #8
    seed=SEED,
    report_to="none",
    dataset_text_field="text",
    packing=False,                              # samples are 7-10k tokens; packing gives no gain and mixes samples
)
# transformers 5 removed warmup_ratio (warmup_steps < 1 is a ratio); TRL 0.2x renamed max_seq_length -> max_length
_kw["warmup_ratio" if "warmup_ratio" in _sig else "warmup_steps"] = 0.03
_kw["max_length" if "max_length" in _sig else "max_seq_length"] = MAX_SEQ_LEN
train_args = SFTConfig(**_kw)

_tr = inspect.signature(SFTTrainer.__init__).parameters
trainer = SFTTrainer(
    model=model,
    **({"processing_class": tokenizer} if "processing_class" in _tr else {"tokenizer": tokenizer}),
    train_dataset=train_ds,
    eval_dataset=val_ds,
    args=train_args,
)

# Loss only on the assistant reply (the code). ~94% of each sample is prompt (rulebook, README,
# variable list); training on it would waste most of the compute memorising the prompt.
from unsloth.chat_templates import train_on_responses_only
trainer = train_on_responses_only(
    trainer,
    instruction_part="<|im_start|>user\n",
    response_part="<|im_start|>assistant\n",
)

# ── Train (resume-able for 14B split sessions) ───────────────────────────────

if RESUME_CKPT and os.path.isdir(RESUME_CKPT):
    print(f"[RESUME] from {RESUME_CKPT}")
    trainer.train(resume_from_checkpoint=RESUME_CKPT)
else:
    trainer.train()

# ── Save final LoRA adapter ──────────────────────────────────────────────────

final_dir = f"{OUTPUT_DIR}/final_lora"
model.save_pretrained(final_dir)
tokenizer.save_pretrained(final_dir)
print(f"[SAVE] LoRA adapter → {final_dir}")

# ── Optional merge+save for Docker (needs disk space) ────────────────────────
# Uncomment after training completes successfully:
# merged_dir = f"{OUTPUT_DIR}/merged_16bit"
# model.save_pretrained_merged(merged_dir, tokenizer, save_method="merged_16bit")
# print(f"[SAVE] merged model → {merged_dir}")
