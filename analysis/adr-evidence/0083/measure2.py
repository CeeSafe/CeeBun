"""Second pass: integer const parameters used as array lengths, per item kind; crates; const fn bodies.
Run: python3 -I measure2.py /Users/kutty/dev/CeeSafeApps/bun/upstream"""
import collections, os, re, sys
ROOT = sys.argv[1]
SKIP = {".git", "node_modules", "target", "test", "tests"}
INTS = {"u8","u16","u32","u64","usize","i8","i16","i32","i64","isize"}
PARAM = re.compile(r"[<,]\s*const\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z_][A-Za-z0-9_:]*)")
ITEM = re.compile(r"\b(fn|struct|enum|impl|trait|union|type)\b")
def strip(s):
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    return re.sub(r"//[^\n]*", "", s)
def body(t, pos):
    i = t.find("{", pos); semi = t.find(";", pos)
    if i < 0 or (0 <= semi < i): return t[pos:semi] if semi >= 0 else ""
    d = 0
    for j in range(i, min(len(t), i + 400000)):
        if t[j] == "{": d += 1
        elif t[j] == "}":
            d -= 1
            if d == 0: return t[i:j+1]
    return t[i:]
crates = collections.Counter(); arr = collections.Counter(); intk = collections.Counter()
cf_kinds = collections.Counter(); cf_total = 0; cf_lines = []
boolfold = collections.Counter()
for d, ds, ns in os.walk(os.path.join(ROOT, "src")):
    ds[:] = [x for x in ds if x not in SKIP]
    for n in ns:
        if not n.endswith(".rs"): continue
        f = os.path.join(d, n); t = strip(open(f, encoding="utf-8", errors="replace").read())
        crate = os.path.relpath(f, os.path.join(ROOT, "src")).split("/")[0]
        for m in PARAM.finditer(t):
            crates[crate] += 1
            name, ty = m.group(1), m.group(2).split("::")[-1]
            head = t[max(0, m.start()-400):m.start()]
            its = list(ITEM.finditer(head)); it = its[-1].group(1) if its else "?"
            if ty in INTS:
                intk[it] += 1
                b = body(t, m.end())
                if re.search(r";\s*\{?\s*" + re.escape(name) + r"\s*\}?\s*\]", b):
                    arr[it] += 1
        for m in re.finditer(r"\bconst\s+(unsafe\s+)?fn\s+\w+[^{;]*\{", t):
            cf_total += 1
            b = body(t, m.end()-1)
            lines = b.count("\n") + 1
            cf_lines.append(lines)
            if re.search(r"\b(loop|while|for)\b", b): cf_kinds["has a loop"] += 1
            if re.search(r"\b(if|match)\b", b): cf_kinds["has if/match"] += 1
            if lines <= 3: cf_kinds["<= 3 lines"] += 1
print("crates", crates.most_common(15))
print("integer params by item", dict(intk))
print("used as array length in the item", dict(arr))
cf_lines.sort()
print("const fn", cf_total, dict(cf_kinds), "median lines", cf_lines[len(cf_lines)//2] if cf_lines else 0)
