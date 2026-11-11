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
            )
        return tokenizer.decode(out[0][in_len:], skip_special_tokens=True)

    return call_llm


# ── vLLM batch path: K candidates per question, execution voting, abstain when unsure ──────
# PA scoring: +1 correct, 0 abstain, -1 wrong -> answer only when candidates agree.
# Thresholds are defaults; calibrate VOTE_MIN_AGREE / VOTE_MIN_SHARE on the hold-out set.
VOTE_K = int(os.environ.get("VOTE_K", "5"))                    # 1 greedy + K-1 sampled candidates
VOTE_TEMP = float(os.environ.get("VOTE_TEMP", "0.7"))
VOTE_MIN_AGREE = int(os.environ.get("VOTE_MIN_AGREE", "2"))    # winning answer needs this many candidates
VOTE_MIN_SHARE = float(os.environ.get("VOTE_MIN_SHARE", "0.4"))  # ...and this share of all candidates
REPAIRS = int(os.environ.get("VOTE_REPAIRS", "2"))             # failed candidates re-asked with real columns
_BIZ_CACHE = {}


def _tables_columns(biz):
    out = []
    for k, v in biz.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict):
            for sheet, df in list(v.items())[:1] + [(s, d) for s, d in v.items() if s == "all"]:
                out.append(f"- `{k}__{sheet}`: {list(map(str, df.columns))}")
        else:
            out.append(f"- `{k}`: {list(map(str, v.columns))}")
    return "\n".join(out)[:4000]


def _exec_worker(args):
    """Pool process (signal.alarm needs the main thread). Returns (ok, type, value, err, columns_on_error)."""
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
        return True, t, v, None, None
    except BaseException as e:  # noqa: BLE001
        cols = _tables_columns(_BIZ_CACHE[biz_dir]) if biz_dir in _BIZ_CACHE else ""
        return False, None, None, f"{type(e).__name__}: {str(e)[:250]}", cols
    finally:
        signal.alarm(0)


def _answer_key(t, v):
    if t == "number":
        try:
            return t, f"{float(v):.6f}"
        except (TypeError, ValueError):
            pass
    if t == "percent":
        try:
            return t, f"{float(str(v).rstrip('%')):.2f}"
        except ValueError:
            pass
    return t, json.dumps(v, ensure_ascii=False, sort_keys=True, default=str)


def _decide(cands, k):
    """cands: list of dicts with ok/type/value/code. Returns (result_fields, votes_summary)."""
    ok = [c for c in cands if c["ok"]]
    tally = {}
    for c in ok:
        tally.setdefault(_answer_key(c["type"], c["value"]), []).append(c)
    votes = sorted(((len(v), key) for key, v in tally.items()), key=lambda x: -x[0])
    summary = {"k": k, "executed": len(ok), "failed": len(cands) - len(ok),
               "votes": [[n, key[0], key[1][:80]] for n, key in votes[:5]]}
    if not votes:
        return None, summary
    n, key = votes[0]
    need = 1 if k == 1 else max(VOTE_MIN_AGREE, VOTE_MIN_SHARE * k)
    tie = len(votes) > 1 and votes[1][0] == n
    if n < need or tie:
        return None, summary
    win = tally[key][0]
    return {"type": win["type"], "answer": win["value"], "_code": win["code"]}, summary


def solve_batch(items, gen, pool, data_root, rulebook, k=None):
    """gen(list_of_message_lists, n, temperature) -> list of n texts per prompt. Backend-agnostic for testing."""
    k = k or VOTE_K
    st = {}
    for it in items:
        try:
            system, prompt, biz_dir = _agent_mod.build_item_prompt(it, data_root, rulebook)
            st[it["id"]] = dict(item=it, msgs=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                                biz=str(biz_dir), cands=[])
        except Exception as e:  # noqa: BLE001
            st[it["id"]] = dict(item=it, err=str(e)[:150], cands=None)
    live = [v for v in st.values() if v["cands"] is not None]

    def run(vs, codes):
        jobs = [(v["biz"], c, v["item"]["as_of_date"]) for v, c in zip(vs, codes)]
        for v, c, r in zip(vs, codes, pool.map(_exec_worker, jobs)):
            v["cands"].append(dict(ok=r[0], type=r[1], value=r[2], err=r[3], cols=r[4], code=c))

    msgs = [v["msgs"] for v in live]
    greedy = gen(msgs, 1, 0.0)
    sampled = gen(msgs, k - 1, VOTE_TEMP) if k > 1 else [[] for _ in live]
    vs, codes = [], []
    for v, g, s in zip(live, greedy, sampled):
        for txt in g + s:
            vs.append(v); codes.append(_agent_mod.extract_code(txt))
    run(vs, codes)

    # Repair: questions without a confident answer re-ask failed candidates with the real column names.
    need_fix = []
    for v in live:
        res, _ = _decide(v["cands"], k)
        if res is None:
            need_fix += [(v, c) for c in [c for c in v["cands"] if not c["ok"]][:REPAIRS]]
    if need_fix:
        fix_msgs = [v["msgs"] + [{"role": "assistant", "content": f"```python\n{c['code']}\n```"},
                                 {"role": "user", "content": f"Error: {c['err']}\nThe tables and their exact column names are:\n"
                                                             f"{c['cols']}\nFix the code. Assign the answer to RESULT."}]
                    for v, c in need_fix]
        outs = gen(fix_msgs, 1, 0.0)
        run([v for v, _ in need_fix], [_agent_mod.extract_code(o[0]) for o in outs])

    results = {}
    for qid, v in st.items():
        if v["cands"] is None:
            results[qid] = {"id": qid, "type": "abstain", "answer": None, "_err": v["err"]}
            continue
        res, summary = _decide(v["cands"], k)
        errs = [c["err"] for c in v["cands"] if c["err"]]
        if res is None:
            best = next((c for c in v["cands"] if c["ok"]), v["cands"][0] if v["cands"] else {})
            results[qid] = {"id": qid, "type": "abstain", "answer": None, "_code": best.get("code"),
                            "_err": errs[0] if errs else "no agreement", "_votes": summary}
        else:
            results[qid] = {"id": qid, **res, "_votes": summary}
    return results


def run_vllm(args, questions, data_root, rulebook, fout, logs_dir, done_ids, chunk=100):
    import multiprocessing as mp
    pool = mp.get_context("fork").Pool(min(8, os.cpu_count() or 2))  # fork BEFORE CUDA init
    from vllm import LLM, SamplingParams
    llm = LLM(model=args.model, dtype="bfloat16", enable_prefix_caching=True,
              max_model_len=24000, gpu_memory_utilization=0.90, tensor_parallel_size=1)
    tok = llm.get_tokenizer()

    def gen(msg_lists, n, temperature):
        texts = [tok.apply_chat_template(m, tokenize=False, add_generation_prompt=True) for m in msg_lists]
        sp = SamplingParams(n=n, temperature=temperature, top_p=1.0 if temperature == 0 else 0.95,
                            max_tokens=2048, seed=1234)
        return [[c.text for c in o.outputs] for o in llm.generate(texts, sp, use_tqdm=False)]

    todo = [q for q in questions if q["id"] not in done_ids]
    n_ans = n_abs = 0
    t_start = time.time()
    for c0 in range(0, len(todo), chunk):
        batch = todo[c0:c0 + chunk]
        t0 = time.time()
        res = solve_batch(batch, gen, pool, data_root, rulebook)
        per_q = (time.time() - t0) / max(len(batch), 1)
        for it in batch:
            r = res[it["id"]]
            _write_result(fout, logs_dir, it, r, per_q)
            n_abs += r.get("type") == "abstain"
            n_ans += r.get("type") != "abstain"
        el = time.time() - t_start
        done = c0 + len(batch)
        print(f"  [{done}/{len(todo)}]  ans={n_ans} abs={n_abs}  ETA={(len(todo)-done)*el/max(done,1)/60:.0f}m", flush=True)
    pool.close()
    return n_ans, n_abs


def _jsonable(o):
    return o.item() if hasattr(o, "item") else str(o)


def to_submission(t, v):
    """Official answer format: percent is a number in percent units (gold: 2.08), not the string '2.08%'."""
    if t == "percent" and isinstance(v, str):
        try:
            return float(v.strip().rstrip("%").replace(",", "."))
        except ValueError:
            return v
    return v


def _write_result(fout, logs_dir, item, result, elapsed):
    """Submission line + per-question log in the official format (Docker guide section 3.3):
    id, answer {type, answer}, elapsed_ms, thinking (null: the model emits code only), code, output."""
    qid = item["id"]
    sub_item = {k: v for k, v in result.items() if not k.startswith("_")}
    sub_item["answer"] = to_submission(sub_item.get("type"), sub_item.get("answer"))
    fout.write(json.dumps(sub_item, ensure_ascii=False, default=_jsonable) + "\n")
    fout.flush()
    log_item = {"id": qid, "answer": {"type": sub_item.get("type"), "answer": sub_item.get("answer")},
                "elapsed_ms": int(round(elapsed * 1000)), "thinking": None,
                "code": result.get("_code"), "output": sub_item.get("answer"),
                "error": result.get("_err"), "votes": result.get("_votes"),
                "business_id": item.get("business_id"), "as_of_date": item.get("as_of_date")}
    (logs_dir / f"{qid}.json").write_text(json.dumps(log_item, ensure_ascii=False, default=_jsonable))


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

            _write_result(fout, logs_dir, item, result, elapsed)

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
