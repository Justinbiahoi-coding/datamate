"""Dump per-question misses for all businesses into JSONL for analysis."""
import sys, json, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import selfgen as S
from loader import load_business
from adapters import _SPECS_RAW, build_spec

ROOT = Path(__file__).parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=15)
    ap.add_argument("--out", default=str(ROOT / "misses.jsonl"))
    args = ap.parse_args()

    qs = [json.loads(l) for l in open(ROOT / "train/questions.jsonl") if l.strip()]
    gold = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "train/answers.jsonl") if l.strip()}
    by_biz = {}
    for q in qs:
        by_biz.setdefault(q["business_id"], []).append(q)

    out = open(args.out, "w", encoding="utf-8")
    total = ok = 0
    for biz, bq in sorted(by_biz.items()):
        bq = bq[: args.sample]
        bd = load_business(ROOT / "train/data" / biz)
        spec = build_spec(bd, _SPECS_RAW[biz])
        fr = S.make_namespace(bd, bq[0]["as_of_date"], spec)
        prods, cats = S.build_match_lists(fr)
        S.GLOBAL_CTX.update(fr)
        for q in bq:
            total += 1
            g = gold[q["id"]]
            gt, ga = g["type"], g["answer"]
            cands, spans = S.gen_candidates(q["question"], q["as_of_date"], spec, fr, prods, cats)
            hit = None
            tried = []
            for c in cands[:10]:
                try:
                    r = S.run_intent(c["code"], fr)
                except Exception as e:
                    r = "ERR:" + str(e)[:80]
                tried.append([c["intent"], c["score"], repr(r)[:120]])
                if S.result_matches_gold(r, gt, ga, g.get("alias", [])):
                    hit = c["intent"]
                    break
            if hit:
                ok += 1
                continue
            out.write(json.dumps({
                "id": q["id"], "biz": biz, "q": q["question"],
                "asof": q["as_of_date"], "type": gt, "gold": ga,
                "spans": [s["label"] for s in spans[:4]],
                "tried": tried,
            }, ensure_ascii=False) + "\n")
    out.close()
    print(f"{ok}/{total} verified, misses -> {args.out}")


if __name__ == "__main__":
    main()
