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
                max_new_tokens=2048,
                do_sample=False,  # greedy cho reproducibility (requirement BTC: |ΔPA|≤0.03)
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                repetition_penalty=1.05,
            )
        return tokenizer.decode(out[0][in_len:], skip_special_tokens=True)

    return call_llm


# ── vLLM batch path (continuous batching + prefix cache) ─────────────────────
_BIZ_CACHE = {}


def _exec_worker(args):
    """Runs in a pool process: signal.alarm works there (main thread), so runaway code is killed."""
    import signal, copy
    biz_dir, code, as_of_date = args
    def _to(*_):
        raise TimeoutError("code timeout")
    signal.signal(signal.SIGALRM, _to)
    signal.alarm(90)
    try:
        if biz_dir not in _BIZ_CACHE:
            _BIZ_CACHE[biz_dir] = _agent_mod.load_business(Path(biz_dir))
        res = _agent_mod.exec_code(code, copy.deepcopy(_BIZ_CACHE[biz_dir]), as_of_date)
        t, v = _agent_mod.infer_type(res)
        return True, t, v, None
    except BaseException as e:  # noqa: BLE001
        return False, None, None, str(e)[:300]
    finally:
        signal.alarm(0)


def run_vllm(args, questions, data_root, rulebook, fout, logs_dir, done_ids, max_retries=2, chunk=100):
    import multiprocessing as mp
    pool = mp.get_context("fork").Pool(min(8, os.cpu_count() or 2))  # fork BEFORE CUDA init
    from vllm import LLM, SamplingParams
    llm = LLM(model=args.model, dtype="bfloat16", enable_prefix_caching=True,
              max_model_len=24000, gpu_memory_utilization=0.90, tensor_parallel_size=1)
    tok = llm.get_tokenizer()
    sp = SamplingParams(temperature=0.0, max_tokens=2048, repetition_penalty=1.05)
    todo = [q for q in questions if q["id"] not in done_ids]
    n_ans = n_abs = 0
    t_start = time.time()
    for c0 in range(0, len(todo), chunk):
        batch = todo[c0:c0 + chunk]
        t0 = time.time()
        st = {}
        for it in batch:
            try:
                system, prompt, biz_dir = _agent_mod.build_item_prompt(it, data_root, rulebook)
                st[it["id"]] = dict(item=it, system=system, prompt=prompt, biz=str(biz_dir), hist=[], code="", err=None, res=None)
            except Exception as e:
                st[it["id"]] = dict(item=it, res={"id": it["id"], "type": "abstain", "answer": None, "_err": str(e)[:150]})
        for attempt in range(max_retries + 1):
            pend = [v for v in st.values() if v["res"] is None]
            if not pend:
                break
            texts = []
            for v in pend:
                msgs = [{"role": "system", "content": v["system"]}] + v["hist"] + \
                       [{"role": "user", "content": v["prompt"] if attempt == 0 else ""}]
                texts.append(tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True))
            outs = llm.generate(texts, sp, use_tqdm=False)
            jobs = []
            for v, o in zip(pend, outs):
                txt = o.outputs[0].text
                if not txt.strip():
                    v["res"] = {"id": v["item"]["id"], "type": "abstain", "answer": None}
                    continue
                v["code"] = _agent_mod.extract_code(txt)
                jobs.append(v)
            for v, r in zip(jobs, pool.map(_exec_worker, [(v["biz"], v["code"], v["item"]["as_of_date"]) for v in jobs])):
                ok, t, ans, err = r
                if ok:
                    v["res"] = {"id": v["item"]["id"], "type": t, "answer": ans, "_code": v["code"]}
                else:
                    v["err"] = err
                    v["hist"] += [{"role": "assistant", "content": f"```python\n{v['code']}\n```"},
                                  {"role": "user", "content": f"Error: {err}\nFix the code."}]
        per_q = (time.time() - t0) / max(len(batch), 1)
        for it in batch:
            v = st[it["id"]]
            res = v["res"] or {"id": it["id"], "type": "abstain", "answer": None, "_err": v.get("err"), "_code": v.get("code")}
            _write_result(fout, logs_dir, it, res, per_q)
            n_abs += res.get("type") == "abstain"
            n_ans += res.get("type") != "abstain"
        el = time.time() - t_start
        done = c0 + len(batch)
        print(f"  [{done}/{len(todo)}]  ans={n_ans} abs={n_abs}  ETA={(len(todo)-done)*el/max(done,1)/60:.0f}m", flush=True)
    pool.close()
    return n_ans, n_abs


def _write_result(fout, logs_dir, item, result, elapsed):
    qid = item["id"]
    sub_item = {k: v for k, v in result.items() if not k.startswith("_")}
    fout.write(json.dumps(sub_item, ensure_ascii=False,
                          default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
    fout.flush()
    log_item = {"id": qid, "biz_id": item.get("business_id"), "question": item.get("question"),
                "as_of_date": item.get("as_of_date"), "answer": sub_item.get("answer"),
                "type": sub_item.get("type"), "elapsed_sec": round(elapsed, 2),
                "code": result.get("_code"), "err": result.get("_err")}
    (logs_dir / f"{qid}.json").write_text(json.dumps(log_item, ensure_ascii=False, indent=2,
                                                     default=lambda o: o.item() if hasattr(o, "item") else str(o)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="/data")
    parser.add_argument("--out", default="/result/submission.jsonl")
    parser.add_argument("--logs", default="/result/logs")
    parser.add_argument("--model", default="/app/models/qwen-datamate")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--backend", choices=["auto", "vllm", "hf"], default="auto")
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

    # ── Resume (shared by both backends) ───────────────────────────────────────
    done_ids = set()
    if out_path.exists():
        with open(out_path, encoding="utf-8") as f:
            for line in f:
                try:
                    done_ids.add(json.loads(line)["id"])
                except Exception:
                    pass
        print(f"[RESUME] {len(done_ids)} câu đã có, sẽ skip", flush=True)

    _agent_mod.ROOT = data_root
    use_vllm = args.backend == "vllm"
    if args.backend == "auto":
        try:
            import vllm  # noqa: F401
            use_vllm = True
        except Exception as e:
            print(f"[BACKEND] vllm unavailable ({e!r}); fallback to transformers (slow)", flush=True)
    if use_vllm:
        print("[BACKEND] vllm", flush=True)
        t_start = time.time()
        with open(out_path, "a" if done_ids else "w", encoding="utf-8") as fout:
            n_ans, n_abs = run_vllm(args, questions, data_root, rulebook, fout, logs_dir, done_ids)
        print(f"\n[DONE] {(time.time()-t_start)/60:.1f}m  answered={n_ans}  abstain={n_abs}")
        return

    # ── Load model + patch call_llm ────────────────────────────────────────────
    model, tokenizer, device = load_model(args.model)
    _agent_mod.call_llm = make_call_llm(model, tokenizer, device)
    _agent_mod.ROOT = data_root  # redirect
    print("[PATCH] agent.call_llm overridden\n", flush=True)

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
