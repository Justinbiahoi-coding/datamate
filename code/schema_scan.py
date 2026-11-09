"""Scan all train businesses and print compact schema info (for building adapters)."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from loader import load_business

ROOT = Path(__file__).parent.parent
split = ROOT / "train" / "data"

def main():
    out = []
    for biz_dir in sorted(split.iterdir()):
        if not biz_dir.is_dir():
            continue
        try:
            d = load_business(biz_dir)
        except Exception as e:
            out.append(f"## {biz_dir.name} LOAD ERROR {e}")
            continue
        out.append(f"\n## {biz_dir.name}")
        for k, v in d.items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict):
                out.append(f"- {k} (dict, sheets={list(v.keys())[:12]})")
                for s, df in list(v.items())[:3]:
                    out.append(f"    {s}: {len(df)} rows | {list(df.columns)}")
            else:
                out.append(f"- {k}: {len(v)} rows | {list(v.columns)}")
    (ROOT / "schema_scan.txt").write_text("\n".join(out), encoding="utf-8")
    print(f"wrote schema_scan.txt ({len(out)} lines)")

if __name__ == "__main__":
    main()
