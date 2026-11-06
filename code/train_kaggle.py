"""QLoRA fine-tuning on Kaggle T4/P100.

Upload sft_data.jsonl to Kaggle as dataset, then run this notebook.

Requirements (Kaggle):
  pip install unsloth accelerate datasets

Model: Qwen2.5-Coder-7B-Instruct (fits T4 16GB comfortably with 4-bit)
       Qwen2.5-Coder-14B-Instruct (fits with Unsloth + gradient checkpointing, ~15GB)
"""

MODEL_NAME = "Qwen/Qwen2.5-Coder-7B-Instruct"
SFT_DATA_PATH = "/kaggle/input/datamate-sft/sft_data.jsonl"
OUTPUT_DIR = "/kaggle/working/lora_out"
MAX_SEQ_LEN = 4096
LORA_RANK = 32
EPOCHS = 3
BATCH_SIZE = 2
GRAD_ACCUM = 4  # effective batch = 8

# ── Setup ────────────────────────────────────────────────────────────────────

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
    lora_alpha=LORA_RANK,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

# ── Dataset ──────────────────────────────────────────────────────────────────

import json
from datasets import Dataset

records = []
with open(SFT_DATA_PATH, encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        # Format as single text string using chat template
        text = tokenizer.apply_chat_template(
            item["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )
        records.append({"text": text})

dataset = Dataset.from_list(records)
print(f"Training on {len(dataset)} examples")

# ── Trainer ──────────────────────────────────────────────────────────────────

from trl import SFTTrainer
from transformers import TrainingArguments

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LEN,
    args=TrainingArguments(
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRAD_ACCUM,
        warmup_steps=5,
        num_train_epochs=EPOCHS,
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=10,
        output_dir=OUTPUT_DIR,
        save_strategy="epoch",
        optim="adamw_8bit",
        lr_scheduler_type="cosine",
        seed=42,
    ),
)

trainer.train()

# ── Save LoRA adapter ────────────────────────────────────────────────────────

model.save_pretrained(OUTPUT_DIR + "/final_lora")
tokenizer.save_pretrained(OUTPUT_DIR + "/final_lora")
print(f"LoRA adapter saved to {OUTPUT_DIR}/final_lora")

# ── Optional: merge + save full model (needs more VRAM/disk) ─────────────────
# model.save_pretrained_merged(OUTPUT_DIR + "/merged", tokenizer, save_method="merged_16bit")
# # Then quantize with AWQ:
# # pip install autoawq
# # python -m awq.entry --model_path merged --quant_path merged_awq --w_bit 4 --q_group_size 128
