"""Debug helper for selfgen: show why questions miss."""
import sys, json, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import selfgen as S
from loader import load_business
from adapters import _SPECS_RAW, build_spec

ROOT = Path(__file__).parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--biz", required=True)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--start", type=int, default=0)
    args = ap.parse_args()
    biz = args.biz
    qs = [json.loads(l) for l in open(ROOT / "train/questions.jsonl") if json.loads(l)["business_id"] == biz]
    qs = qs[args.start: args.start + args.n]
    gold = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "train/answers.jsonl")}
    bd = load_business(ROOT / "train/data" / biz)
    spec = build_spec(bd, _SPECS_RAW[biz])
    fr = S.make_namespace(bd, qs[0]["as_of_date"], spec)
    prods, cats = S.build_match_lists(fr)
    S.GLOBAL_CTX.update(fr)
    for q in qs:
        g = gold[q["id"]]
        gt, ga = g["type"], g["answer"]
        cands, spans = S.gen_candidates(q["question"], q["as_of_date"], spec, fr, prods, cats)
        hit = None
        for c in cands[:8]:
            try:
                r = S.run_intent(c["code"], fr)
            except Exception as e:
                r = "ERR:" + str(e)[:60]
            if S.result_matches_gold(r, gt, ga, g.get("alias", [])):
                hit = (c["intent"], r)
                break
        if hit:
            continue
        print(f"MISS [{gt}] {q['question'][:110]} => {ga!r}")
        print("   span:", spans[0]["label"] if spans else None,
              "cands:", [(c["intent"], c["score"]) for c in cands[:6]])
        for c in cands[:4]:
            try:
                r = S.run_intent(c["code"], fr)
            except Exception as e:
                r = "ERR:" + str(e)[:60]
            print("     ", c["intent"], "->", repr(r)[:100])


if __name__ == "__main__":
    main()
