"""Convert the 569 retry9 solutions that depend on /tmp/s9_* helpers into self-contained code.

Reads:  sub_final2.jsonl + sub_haiku/retry9_*.jsonl + audit_dependent.json + backup_s9/
Writes: sub_selfcontained/retry9_fix.jsonl and unfixed.json

Usage:
    python3 sub_selfcontained/convert_retry9.py [--limit N]

The conversion is mechanical: it inlines the helper module used by each row, replaces the
load_business() calls with the sandbox `data` variable, tree-shakes unused helpers, and
renames helper symbols with an `_h_` prefix. Every produced answer is executed and compared
with the stored `answer` before it is written.
"""
import argparse, ast, copy, json, re, sys, traceback
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
from loader import load_business  # noqa: E402
from agent import exec_code  # noqa: E402

BACK = ROOT / "backup_s9"
OUT = ROOT / "sub_selfcontained"

SAFE_IMPORTS = {"re", "unicodedata", "pandas", "numpy", "math", "datetime", "decimal",
                "collections", "itertools", "functools", "statistics"}
DROP_IMPORTS = {"sys", "pathlib", "importlib", "subprocess", "os"}
FORBIDDEN = [
    (r"sys\.path", "sys.path"), (r"load_business", "load_business"),
    (r"train/data|train\\data", "train/data"),
    (r"/tmp|/Users/", "absolute path"), (r"\bopen\(", "open()"),
    (r"^\s*(import|from)\s+(h\d*|loader|selfgen|adapters|_h)\b", "helper import"),
    (r"^\s*import\s+\w+\s*,\s*h\d*\b", "helper import"),
    (r"\bimportlib\b|\bsubprocess\b|\bos\.system\b", "dynamic import/exec"),
]


def load_rows():
    rows = {}
    for line in open(ROOT / "sub_final2.jsonl"):
        r = json.loads(line)
        rows[r["id"]] = r
    for f in sorted((ROOT / "sub_haiku").glob("retry9_*.jsonl")):
        for line in open(f):
            r = json.loads(line)
            rows[r["id"]] = r
    return rows


def _num(x):
    if isinstance(x, bool):
        return None
    try:
        return float(str(x).rstrip("%").replace(",", ""))
    except Exception:
        return None


def _decimals(x):
    s = str(x).rstrip("%")
    return len(s.split(".")[1]) if "." in s else 0


def _round_half_up(x, d):
    q = Decimal("1") if d == 0 else Decimal("1." + "0" * d)
    return float(Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP))


def same(pred, stored, typ):
    if stored is None:
        return pred is None
    if typ in ("number", "percent"):
        p, g = _num(pred), _num(stored)
        if p is None or g is None:
            return False
        d = _decimals(stored)
        return abs(_round_half_up(p, d) - g) <= 1e-9 or abs(p - g) <= max(1e-9, 1e-7 * abs(g))
    if typ == "list":
        if not (isinstance(pred, list) and isinstance(stored, list)) or len(pred) != len(stored):
            return False
        return all(str(a) == str(b) for a, b in zip(pred, stored))
    return str(pred).strip() == str(stored).strip()


def helper_info(code):
    m = re.search(r"sys\.path\.insert\(\s*0\s*,\s*'/tmp/(s9_\d+)'\s*\)", code)
    if not m:
        return None
    mm = re.search(r"^\s*import\s+(h\d*)(?:\s+as\s+(\w+))?", code, re.M)
    if not mm:
        return None
    return m.group(1), mm.group(1), mm.group(2) or "h"


class Rename(ast.NodeTransformer):
    def __init__(self, mp):
        self.mp = mp

    def visit_Name(self, n):
        if n.id in self.mp:
            return ast.copy_location(ast.Name(id=self.mp[n.id], ctx=n.ctx), n)
        return n

    def visit_FunctionDef(self, n):
        if n.name in self.mp:
            n.name = self.mp[n.name]
        self.generic_visit(n)
        return n

    def visit_ClassDef(self, n):
        if n.name in self.mp:
            n.name = self.mp[n.name]
        self.generic_visit(n)
        return n

    def visit_Assign(self, n):
        for t in n.targets:
            if isinstance(t, ast.Name) and t.id in self.mp:
                t.id = self.mp[t.id]
        self.generic_visit(n)
        return n

    def visit_Global(self, n):
        n.names = [self.mp.get(x, x) for x in n.names]
        return n


class LoaderToData(ast.NodeTransformer):
    def visit_Call(self, n):
        self.generic_visit(n)
        if isinstance(n.func, ast.Name) and n.func.id == "load_business":
            return ast.copy_location(ast.Name(id="data", ctx=ast.Load()), n)
        if isinstance(n.func, ast.Attribute) and n.func.attr == "load_business":
            return ast.copy_location(ast.Name(id="data", ctx=ast.Load()), n)
        return n


def build(helper_path, alias, qcode, special_t109=False):
    tree = ast.parse(Path(helper_path).read_text())
    imports, body = [], []
    for n in tree.body:
        if isinstance(n, ast.Expr):
            continue
        if isinstance(n, ast.Import):
            keep = [a for a in n.names if a.name.split(".")[0] in SAFE_IMPORTS]
            if keep:
                imports.append(ast.Import(names=keep))
        elif isinstance(n, ast.ImportFrom):
            base = (n.module or "").split(".")[0]
            if base in SAFE_IMPORTS:
                imports.append(n)
        else:
            body.append(n)
    tree.body = body
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == "biz":
            n.body = [ast.Return(value=ast.Name(id="data", ctx=ast.Load()))]
    tree = LoaderToData().visit(tree)
    ast.fix_missing_locations(tree)

    defs = {}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            defs[n.name] = n
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    defs[t.id] = n
    seeds = {"tables"} if special_t109 else set(re.findall(rf"\b{re.escape(alias)}\.(\w+)\b", qcode))
    seeds = {s for s in seeds if s in defs and s not in ("ROOT", "load_business")}
    need, stack = set(), list(seeds)
    while stack:
        k = stack.pop()
        if k in need or k not in defs:
            continue
        need.add(k)
        for x in ast.walk(defs[k]):
            if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load) and x.id in defs:
                stack.append(x.id)

    selected = []
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            if n.name in need:
                selected.append(n)
        elif isinstance(n, ast.Assign):
            names = [t.id for t in n.targets if isinstance(t, ast.Name)]
            if "ROOT" not in names and any(x in need for x in names):
                selected.append(n)
        else:
            selected.append(n)

    params = set()
    for n in selected:
        if isinstance(n, ast.FunctionDef):
            params.update(a.arg for a in n.args.args + n.args.kwonlyargs)
            if n.args.vararg:
                params.add(n.args.vararg.arg)
            if n.args.kwarg:
                params.add(n.args.kwarg.arg)
    collisions = {k for k in need if k in params}
    if collisions:
        raise RuntimeError(f"helper/top-level name collision: {sorted(collisions)}")

    mod = ast.Module(body=imports + selected, type_ignores=[])
    mod = Rename({k: "_h_" + k for k in need}).visit(mod)
    ast.fix_missing_locations(mod)
    helper_src = ast.unparse(mod)

    lines = []
    for line in qcode.splitlines():
        s = line.strip()
        if re.match(r"^import\s+sys\s*$", s) or re.match(r"^import\s+sys\s+as\s+\w+\s*$", s):
            continue
        m = re.match(r"^import\s+sys\s*,\s*(.+)$", s)
        if m:
            lines.append("import " + m.group(1))
            continue
        if re.match(r"^\w+\.path\.insert\(", s):
            continue
        if re.match(r"^from\s+pathlib\s+import", s) or re.match(r"^from\s+loader\s+import", s):
            continue
        if re.match(r"^_b\s*=\s*_lb\(", s) or re.match(r"^_b\s*=\s*load_business\(", s):
            lines.append("_b = data")
            continue
        if re.match(r"^import\s+h\d*(\s+as\s+\w+)?\s*$", s):
            continue
        if re.match(r"^import\s+h\d*\s*,", s):
            rest = s.split(",", 1)[1].strip()
            if rest:
                lines.append("import " + rest)
            continue
        if "/tmp" in s or "/Users" in s:
            continue
        lines.append(line)
    q = "\n".join(lines)
    q = re.sub(rf"\b{re.escape(alias)}\.load_business\([^()]*\)", "data", q)
    q = re.sub(r"\b_lb\([^()]*\)", "data", q)
    q = re.sub(r"\bload_business\([^()]*\)", "data", q)
    if special_t109:
        q = re.sub(rf"\b{re.escape(alias)}\.t109\(", "_h_tables(", q)
    else:
        q = re.sub(rf"\b{re.escape(alias)}\.", "_h_", q)
    return helper_src + "\n\n" + q


def pick_helper(code):
    info = helper_info(code)
    if not info:
        return None
    d, mod, alias = info
    path = BACK / d / f"{mod}.py"
    if not path.exists():
        return None
    special = d == "s9_007" and bool(re.search(rf"\b{re.escape(alias)}\.t109\(", code))
    if special:
        path = BACK / "s9_006" / "h.py"
    return path, alias, special


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    rows = load_rows()
    qs = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "train/questions.jsonl")}
    dep = json.load(open(ROOT / "audit_dependent.json"))["dependent"]
    if a.limit:
        dep = dep[: a.limit]
    fixed, unfixed, sizes = [], [], []
    for i, qid in enumerate(dep, 1):
        r = rows[qid]
        biz = qs[qid]["business_id"]
        try:
            info = pick_helper(r["_code"])
            if not info:
                raise RuntimeError("no helper info")
            code = build(info[0], info[1], r["_code"], info[2])
            ast.parse(code)
            why = [name for pat, name in FORBIDDEN if re.search(pat, code, re.M)]
            if why:
                raise RuntimeError("static: " + ",".join(why))
            data = copy.deepcopy(load_business(ROOT / "train" / "data" / biz))
            val = exec_code(code, data, qs[qid]["as_of_date"])
            if not same(val, r["answer"], r["type"]):
                raise RuntimeError(f"answer mismatch: stored={r['answer']!r} got={val!r}")
            out = dict(r)
            out["_code"] = code
            out["_verdict"] = "correct"
            fixed.append(out)
            sizes.append(len(code))
        except Exception as e:
            unfixed.append({"id": qid, "error": repr(e)[:300]})
            print("FAIL", qid, biz, repr(e)[:160], flush=True)
        if i % 50 == 0:
            print("progress", i, "ok", len(fixed), "fail", len(unfixed), flush=True)
    OUT.mkdir(exist_ok=True)
    with open(OUT / "retry9_fix.jsonl", "w") as f:
        for r in fixed:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    json.dump(unfixed, open(OUT / "unfixed.json", "w"), ensure_ascii=False, indent=1)
    json.dump([r["id"] for r in fixed], open(OUT / "ids.json", "w"))
    if sizes:
        sizes.sort()
        print("DONE ok", len(fixed), "unfixed", len(unfixed),
              "chars min/median/p90/max", sizes[0], sizes[len(sizes) // 2],
              sizes[int(len(sizes) * 0.9)], sizes[-1])


if __name__ == "__main__":
    main()
