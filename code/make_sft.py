"""Generate verified SFT training data for DataMate fine-tuning.

Strategy (execution-based filtering):
  For each (question, gold_answer) in train:
    1. Build prompt with business schema + rulebook + question
    2. Call a code-gen model to generate N candidate codes
    3. Execute each candidate; compare output with gold answer
    4. Save passing (prompt, code) pairs as SFT data

Output: sft_data.jsonl  (each line: {id, messages: [{role,content},...]} )

Usage:
  # Generate via Claude API (fast, needs ANTHROPIC_API_KEY)
  python make_sft.py --generator claude --limit 100 --out sft_data.jsonl

  # Generate via local vLLM endpoint
  python make_sft.py --generator vllm --vllm-url http://localhost:8000 --limit 100

  # Dry-run: just show what prompts look like
  python make_sft.py --dry-run --limit 3
"""
import json
import sys
import argparse
import textwrap
import traceback
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from loader import load_business, describe_business  # noqa: E402
from scorer import match_answer  # noqa: E402
from agent import exec_code, infer_type, SYSTEM_PROMPT, build_prompt, extract_code  # noqa: E402


# ── Gold answer matching ─────────────────────────────────────────────────────

def result_matches_gold(result: Any, gold_type: str, gold_ans: Any, alias: list) -> bool:
    """Check if executed result matches gold answer."""
    if result is None:
        return gold_ans is None or gold_type == "unanswerable"
    if gold_ans is None:
        return str(result).lower() in ("unanswerable", "none", "null", "")

    pred_type, pred_val = infer_type(result)
    return match_answer(pred_type, pred_val, gold_type, gold_ans, alias)


# ── Code generators ──────────────────────────────────────────────────────────

def generate_via_claude(prompt: str, n: int = 3) -> list[str]:
    """Generate N candidate codes using Anthropic API."""
    import anthropic
    client = anthropic.Anthropic()

    candidates = []
    for _ in range(n):
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text
        candidates.append(extract_code(raw))
    return candidates


def generate_via_gemini(prompt: str, n: int = 3) -> list[str]:
    """Generate N candidate codes using Gemini API (free tier)."""
    import os, time as _time
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
    )
    candidates = []
    for _ in range(n):
        for attempt in range(3):
            try:
                resp = model.generate_content(prompt, generation_config={"max_output_tokens": 1200, "temperature": 0.7})
                candidates.append(extract_code(resp.text))
                _time.sleep(2)
                break
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    _time.sleep(30)
                else:
                    raise
    return candidates


def generate_via_groq(prompt: str, n: int = 3) -> list[str]:
    """Generate N candidate codes using Groq API (free tier)."""
    import os
    from openai import OpenAI
    client = OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
    )
    import time as _time
    candidates = []
    for _ in range(n):
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model="qwen/qwen3.8-27b",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=900,
                    temperature=0.7,
                )
                raw = resp.choices[0].message.content
                candidates.append(extract_code(raw))
                _time.sleep(3)  # respect rate limit
                break
            except Exception as e:
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    _time.sleep(30)
                else:
                    raise
    return candidates


def generate_via_vllm(prompt: str, n: int = 3, url: str = "http://localhost:8000") -> list[str]:
    """Generate N candidate codes via vLLM OpenAI-compatible API."""
    import requests
    payload = {
        "model": "Qwen2.5-Coder-14B-Instruct-AWQ",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1024,
        "n": n,
        "temperature": 0.8,
    }
    resp = requests.post(f"{url}/v1/chat/completions", json=payload, timeout=60)
    resp.raise_for_status()
    choices = resp.json()["choices"]
    return [extract_code(c["message"]["content"]) for c in choices]


# ── SFT message formatter ────────────────────────────────────────────────────

def make_messages(prompt: str, code: str) -> list[dict]:
    """Format as chat messages for SFT training."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": f"```python\n{code}\n```"},
    ]


# ── Main pipeline ─────────────────────────────────────────────────────────────

def process_question(item, gold, split_root, rulebook,
                     generator, n_candidates, vllm_url):
    """Try to find a verified code for one question. Returns SFT record or None."""
    biz_id = item["business_id"]
    biz_dir = split_root / "data" / biz_id

    try:
        biz_data = load_business(biz_dir)
        biz_schema = describe_business(biz_dir)
    except Exception as e:
        return None

    prompt = build_prompt(item["question"], item["as_of_date"], biz_schema, rulebook[:2000])

    if generator == "claude":
        candidates = generate_via_claude(prompt, n=n_candidates)
    elif generator == "gemini":
        candidates = generate_via_gemini(prompt, n=n_candidates)
    elif generator == "groq":
        candidates = generate_via_groq(prompt, n=n_candidates)
    elif generator == "vllm":
        candidates = generate_via_vllm(prompt, n=n_candidates, url=vllm_url)
    else:
        raise ValueError(f"Unknown generator: {generator}")

    gold_type = gold["type"]
    gold_ans = gold["answer"]
    alias = gold.get("alias", [])

    for code in candidates:
        try:
            result = exec_code(code, biz_data, item["as_of_date"])
            if result_matches_gold(result, gold_type, gold_ans, alias):
                return {
                    "id": item["id"],
                    "messages": make_messages(prompt, code),
                    "gold_type": gold_type,
                    "gold_answer": gold_ans,
                }
        except Exception:
            continue

    return None  # no candidate passed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generator", choices=["claude", "gemini", "groq", "vllm"], default="gemini")
    parser.add_argument("--vllm-url", default="http://localhost:8000")
    parser.add_argument("--n-candidates", type=int, default=3,
                        help="Number of code candidates to try per question")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out", default="sft_data.jsonl")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print first few prompts without calling LLM")
    parser.add_argument("--data-dir", default=None)
    args = parser.parse_args()

    base = Path(args.data_dir) if args.data_dir else ROOT
    split_root = base / "train"

    if not split_root.exists():
        print(f"Train root not found: {split_root}")
        sys.exit(1)

    rulebook = (split_root / "rulebook.md").read_text(encoding="utf-8")

    with open(split_root / "questions.jsonl", encoding="utf-8") as f:
        questions = [json.loads(l) for l in f if l.strip()]
    with open(split_root / "answers.jsonl", encoding="utf-8") as f:
        gold_index = {json.loads(l)["id"]: json.loads(l) for l in f if l.strip()}

    if args.limit:
        questions = questions[: args.limit]

    if args.dry_run:
        for item in questions[:3]:
            biz_dir = split_root / "data" / item["business_id"]
            biz_schema = describe_business(biz_dir)
            prompt = build_prompt(item["question"], item["as_of_date"], biz_schema, rulebook[:2000])
            print(f"\n{'='*60}")
            print(f"Q: {item['question']}")
            print(f"Gold: {gold_index[item['id']]['type']} = {gold_index[item['id']]['answer']}")
            print(f"\nPrompt (first 800 chars):\n{prompt[:800]}")
        return

    out_path = Path(args.out)
    n_success = n_fail = 0
    t0 = time.time()

    with open(out_path, "w", encoding="utf-8") as fout:
        for i, item in enumerate(questions):
            gold = gold_index.get(item["id"])
            if gold is None:
                continue

            try:
                record = process_question(
                    item, gold, split_root, rulebook,
                    args.generator, args.n_candidates, args.vllm_url,
                )
            except Exception:
                record = None

            if record:
                fout.write(json.dumps(record, ensure_ascii=False) + "\n")
                n_success += 1
            else:
                n_fail += 1

            if (i + 1) % 10 == 0:
                elapsed = time.time() - t0
                rate = (i + 1) / elapsed
                eta = (len(questions) - i - 1) / rate
                print(f"  [{i+1}/{len(questions)}]  ok={n_success}  fail={n_fail}  "
                      f"rate={rate:.1f}q/s  ETA={eta/60:.0f}m", flush=True)

    print(f"\nDone → {out_path}  ({n_success} verified, {n_fail} failed)")
    print(f"Success rate: {n_success/(n_success+n_fail)*100:.1f}%")


if __name__ == "__main__":
    main()
