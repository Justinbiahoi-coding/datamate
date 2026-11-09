"""Evaluate fine-tuned model on held-out train questions.

Loads LoRA adapter, runs inference on N random train questions,
compares vs gold via scorer.match_answer, prints per-type breakdown.

Usage:
  # Kaggle (after train finishes):
  python eval_finetune.py \
    --base-model Qwen/Qwen2.5-Coder-7B-Instruct \
    --lora /kaggle/working/lora_out/final_lora \
    --data-dir /kaggle/input/datamate-raw \
    --n 200 --seed 42
"""
import os, sys, json, time, random, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import agent as _agent_mod
from agent import infer as _agent_infer, SYSTEM_PROMPT
from scorer import match_answer


def load_model_with_lora(base_model: str, lora_path: str, use_4bit: bool = True):
    """Load base + attach LoRA adapter."""
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    from peft import PeftModel

    print(f"[LOAD] tokenizer")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token_id is None or tokenizer.pad_token_id == tokenizer.eos_token_id:
        tokenizer.pad_token = "<|endoftext|>"
        try:
            tokenizer.pad_token_id = tokenizer.convert_tokens_to_ids("<|endoftext|>")
        except Exception:
            tokenizer.pad_token_id = 151643

    print(f"[LOAD] base model (4bit={use_4bit})")
    kwargs = {"device_map": "auto", "trust_remote_code": True}
    if use_4bit:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True, bnb_4bit_quant_type="nf4",
        )
    else:
        kwargs["torch_dtype"] = torch.bfloat16

    model = AutoModelForCausalLM.from_pretrained(base_model, **kwargs)
    print(f"[LOAD] attach LoRA from {lora_path}")
    model = PeftModel.from_pretrained(model, lora_path)
    model.eval()
    device = next(model.parameters()).device
    return model, tokenizer, device


def make_call_llm(model, tokenizer, device):
    import torch
    def call_llm(prompt, system=None, history=None):
        if system is None:
            system = SYSTEM_PROMPT
        messages = history or []
        msgs = [{"role": "system", "content": system}] + messages + \
               [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=14000).to(device)
        with torch.no_grad():
            out = model.generate(
                **inputs, max_new_tokens=1200, do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                repetition_penalty=1.05,
            )
        return tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return call_llm


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument("--lora", required=True, help="path to LoRA adapter dir")
    parser.add_argument("--data-dir", default=".", help="project root (chứa train/)")
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="eval_result.jsonl")
    parser.add_argument("--no-4bit", action="store_true", help="load fp16 (more VRAM)")
    args = parser.parse_args()

    split_root = Path(args.data_dir) / "train"
    with open(split_root / "questions.jsonl", encoding="utf-8") as f:
        questions = [json.loads(l) for l in f if l.strip()]
    with open(split_root / "answers.jsonl", encoding="utf-8") as f:
        gold_index = {json.loads(l)["id"]: json.loads(l) for l in f if l.strip()}
    rulebook = (split_root / "rulebook.md").read_text(encoding="utf-8")

    # Sample N random questions reproducibly
    rng = random.Random(args.seed)
    sample = rng.sample(questions, min(args.n, len(questions)))
    print(f"[EVAL] {len(sample)} câu  seed={args.seed}")

    model, tokenizer, device = load_model_with_lora(args.base_model, args.lora, use_4bit=not args.no_4bit)
    _agent_mod.call_llm = make_call_llm(model, tokenizer, device)

    # Per-type counters
    per_type = {}
    n_ok = n_wrong = n_abs = 0
    t_start = time.time()

    with open(args.out, "w", encoding="utf-8") as fout:
        for i, item in enumerate(sample):
            gold = gold_index.get(item["id"])
            if gold is None:
                continue
            gold_type = gold["type"] if gold["answer"] is not None else "unanswerable"
            per_type.setdefault(gold_type, {"correct": 0, "wrong": 0, "abstain": 0})

            try:
                result = _agent_infer(item, split_root, rulebook)
            except Exception as e:
                result = {"id": item["id"], "type": "abstain", "answer": None, "_err": str(e)[:150]}

            pred_type = result.get("type", "abstain")
            pred_ans = result.get("answer")

            if pred_type == "abstain" or pred_ans is None:
                per_type[gold_type]["abstain"] += 1
                n_abs += 1
                verdict = "abstain"
            elif gold["answer"] is None:
                if pred_type == "unanswerable":
                    per_type[gold_type]["correct"] += 1; n_ok += 1; verdict = "correct"
                else:
                    per_type[gold_type]["wrong"] += 1; n_wrong += 1; verdict = "wrong"
            elif match_answer(pred_type, pred_ans, gold["type"], gold["answer"], gold.get("alias", [])):
                per_type[gold_type]["correct"] += 1; n_ok += 1; verdict = "correct"
            else:
                per_type[gold_type]["wrong"] += 1; n_wrong += 1; verdict = "wrong"

            fout.write(json.dumps({
                "id": item["id"],
                "gold_type": gold_type,
                "gold_answer": gold["answer"],
                "pred_type": pred_type,
                "pred_answer": pred_ans,
                "verdict": verdict,
            }, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, 'item') else str(o)) + "\n")
            fout.flush()

            if (i + 1) % 10 == 0:
                rate = (i + 1) / (time.time() - t_start)
                print(f"  [{i+1}/{len(sample)}]  ok={n_ok} wr={n_wrong} abs={n_abs}  {rate:.2f}q/s", flush=True)

    # Final report
    total = n_ok + n_wrong + n_abs
    score = n_ok - n_wrong
    print(f"\n{'='*60}")
    print(f"EVAL RESULT")
    print(f"{'='*60}")
    print(f"Total: {total}  correct={n_ok}  wrong={n_wrong}  abstain={n_abs}")
    print(f"Score: {score}/{total}  ({score/total*100:.1f}%)")
    print(f"Accuracy on answered: {n_ok/(n_ok+n_wrong)*100:.1f}%" if (n_ok+n_wrong) else "No answered")

    print(f"\n{'─'*60}")
    print(f"{'type':<14} {'total':>6} {'✓':>5} {'✗':>5} {'∅':>5} {'acc':>7}")
    print("-" * 60)
    for t in sorted(per_type):
        c = per_type[t]
        tot = c["correct"] + c["wrong"] + c["abstain"]
        acc = c["correct"]/(c["correct"]+c["wrong"])*100 if (c["correct"]+c["wrong"]) else 0
        print(f"{t:<14} {tot:>6} {c['correct']:>5} {c['wrong']:>5} {c['abstain']:>5} {acc:>6.1f}%")


if __name__ == "__main__":
    main()
