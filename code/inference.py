"""DataMate Docker inference entrypoint.

Chạy fully offline. Load Qwen base + LoRA merged từ /app/models/, loop qua questions,
ghi submission + per-question logs.

Args:
  --data-root    Split root (chứa questions.jsonl, rulebook.md, data/, calendar.csv).
                 Thường là /data (mount bởi BTC). Default: /data.
  --out          Output submission.jsonl. Default: /result/submission.jsonl.
  --logs         Per-question logs dir. Default: /result/logs/.
  --model        Path to merged model. Default: /app/models/qwen-datamate.
  --limit        Chỉ chạy N câu đầu (debug). Default: all.
"""
import os, sys, json, time, argparse, traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Agent reuse: helpers & logic
import agent as _agent_mod
from agent import infer as _agent_infer  # noqa: E402


def load_model(model_path: str):
    """Load fine-tuned model, inject vào agent module."""
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM

    print(f"[LOAD] model from {model_path}", flush=True)
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    if tokenizer.pad_token_id is None or tokenizer.pad_token_id == tokenizer.eos_token_id:
        tokenizer.pad_token = "<|endoftext|>"
        try:
            tokenizer.pad_token_id = tokenizer.convert_tokens_to_ids("<|endoftext|>")
        except Exception:
            tokenizer.pad_token_id = 151643

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
        local_files_only=True,
    )
    model.eval()
    device = next(model.parameters()).device
    print(f"[LOAD] done in {time.time()-t0:.1f}s  device={device}  "
          f"VRAM={torch.cuda.memory_allocated()//1024//1024}MB", flush=True)
    return model, tokenizer, device


def make_call_llm(model, tokenizer, device):
    """Return call_llm function bound to this model."""
    import torch

    def call_llm(prompt, system=None, history=None):
        if system is None:
            system = _agent_mod.SYSTEM_PROMPT
        messages = history or []
        msgs = [{"role": "system", "content": system}] + messages + \
               [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt",
                           truncation=True, max_length=20000).to(device)
        in_len = inputs["input_ids"].shape[1]
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=1200,
                do_sample=False,  # greedy cho reproducibility (requirement BTC: |ΔPA|≤0.03)
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                repetition_penalty=1.05,
            )
        return tokenizer.decode(out[0][in_len:], skip_special_tokens=True)

    return call_llm


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="/data")
    parser.add_argument("--out", default="/result/submission.jsonl")
    parser.add_argument("--logs", default="/result/logs")
    parser.add_argument("--model", default="/app/models/qwen-datamate")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    data_root = Path(args.data_root)
    out_path = Path(args.out)
    logs_dir = Path(args.logs)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # ── Load questions + rulebook ─────────────────────────────────────────────
    questions_path = data_root / "questions.jsonl"
    rulebook_path = data_root / "rulebook.md"
    if not questions_path.exists():
        sys.exit(f"[FATAL] not found: {questions_path}")
    if not rulebook_path.exists():
        sys.exit(f"[FATAL] not found: {rulebook_path}")

    with open(questions_path, encoding="utf-8") as f:
        questions = [json.loads(l) for l in f if l.strip()]
    rulebook = rulebook_path.read_text(encoding="utf-8")
    if args.limit:
        questions = questions[:args.limit]
    print(f"[QUEST] {len(questions)} câu từ {questions_path}", flush=True)

    # ── Load model + patch call_llm ────────────────────────────────────────────
    model, tokenizer, device = load_model(args.model)
    _agent_mod.call_llm = make_call_llm(model, tokenizer, device)
    _agent_mod.ROOT = data_root  # redirect
    print("[PATCH] agent.call_llm overridden\n", flush=True)

    # ── Resume: nếu out đã có câu → skip ──────────────────────────────────────
    done_ids = set()
    if out_path.exists():
        with open(out_path, encoding="utf-8") as f:
            for line in f:
                try:
                    done_ids.add(json.loads(line)["id"])
                except Exception:
                    pass
        print(f"[RESUME] {len(done_ids)} câu đã có, sẽ skip", flush=True)

    # ── Inference loop với per-question logging ────────────────────────────────
    mode = "a" if done_ids else "w"
    n_ans = n_abs = 0
    t_start = time.time()

    with open(out_path, mode, encoding="utf-8") as fout:
        for i, item in enumerate(questions):
            qid = item["id"]
            if qid in done_ids:
                continue

            t0 = time.time()
            try:
                result = _agent_infer(item, data_root, rulebook)
            except Exception as e:
                result = {"id": qid, "type": "abstain", "answer": None,
                          "_err": f"fatal:{str(e)[:150]}"}
                traceback.print_exc(file=sys.stderr)
            elapsed = time.time() - t0

            # Submission line: strip internal keys
            sub_item = {k: v for k, v in result.items() if not k.startswith("_")}
            fout.write(json.dumps(sub_item, ensure_ascii=False,
                                  default=lambda o: o.item() if hasattr(o, 'item') else str(o)) + "\n")
            fout.flush()

            # Per-question log (requirement BTC)
            log_item = {
                "id": qid,
                "biz_id": item.get("business_id"),
                "question": item.get("question"),
                "as_of_date": item.get("as_of_date"),
                "answer": sub_item.get("answer"),
                "type": sub_item.get("type"),
                "elapsed_sec": round(elapsed, 2),
                "code": result.get("_code"),
                "err": result.get("_err"),
            }
            (logs_dir / f"{qid}.json").write_text(
                json.dumps(log_item, ensure_ascii=False, indent=2,
                           default=lambda o: o.item() if hasattr(o, 'item') else str(o))
            )

            if result.get("type") == "abstain":
                n_abs += 1
            else:
                n_ans += 1

            if (i + 1) % 10 == 0:
                total_elapsed = time.time() - t_start
                rate = (i + 1) / total_elapsed
                eta = (len(questions) - i - 1) / rate if rate > 0 else 0
                print(f"  [{i+1}/{len(questions)}]  ans={n_ans} abs={n_abs}  "
                      f"{rate:.2f}q/s  ETA={eta/60:.0f}m", flush=True)

    total = time.time() - t_start
    print(f"\n[DONE] {total/60:.1f}m  answered={n_ans}  abstain={n_abs}")
    print(f"[OUT]  {out_path}  ({n_ans + n_abs} lines)")
    print(f"[LOGS] {logs_dir}/  ({n_ans + n_abs} files)")


if __name__ == "__main__":
    main()
