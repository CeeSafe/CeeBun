"""Measure const generics and const fn in Bun's Rust (src/, same SKIP as analysis/bun_rust_features.py).

Run: python3 -I measure.py ../../../upstream
"""
import collections
import os
import re
import sys

ROOT = sys.argv[1]
SKIP = {".git", "node_modules", "target", "test", "tests"}
INTS = {"u8", "u16", "u32", "u64", "usize", "i8", "i16", "i32", "i64", "isize", "u128", "i128", "char"}

files = []
for d, dirs, names in os.walk(os.path.join(ROOT, "src")):
    dirs[:] = [x for x in dirs if x not in SKIP]
    for n in names:
        if n.endswith(".rs"):
            files.append(os.path.join(d, n))

def strip_comments(s):
    s = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), s, flags=re.S)
    return re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), s)

PARAM = re.compile(r"[<,]\s*const\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z_][A-Za-z0-9_:]*)")
ITEM = re.compile(r"\b(fn|struct|enum|impl|trait|union|type)\b")
CONSTFN = re.compile(r"\bconst\s+(unsafe\s+)?fn\b")
TURBO = re.compile(r"::<")
SCRIPT_ONLY = "regex"

kind = collections.Counter()
site = collections.Counter()
enum_types = collections.Counter()
params_per_item = collections.Counter()
use = collections.Counter()
fn_params = 0
examples = collections.defaultdict(list)
const_fn = 0
const_fn_files = collections.Counter()
param_names = set()
total = 0
items_with = set()
gce = 0

def body_after(text, pos):
    """The brace-balanced body of the item whose header contains pos; '' for a declaration without one."""
    i = text.find("{", pos)
    semi = text.find(";", pos)
    if i < 0 or (0 <= semi < i):
        return ""
    depth = 0
    for j in range(i, min(len(text), i + 200000)):
        c = text[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
    return text[i:]

texts = {}
for f in files:
    try:
        t = strip_comments(open(f, encoding="utf-8", errors="replace").read())
    except OSError:
        continue
    texts[f] = t
    for m in CONSTFN.finditer(t):
        const_fn += 1
        const_fn_files[os.path.relpath(f, ROOT).split("/")[1]] += 1
    for m in PARAM.finditer(t):
        name, ty = m.group(1), m.group(2)
        total += 1
        param_names.add(name)
        base = ty.split("::")[-1]
        if base == "bool":
            k = "bool"
        elif base in INTS:
            k = "integer:" + base
        else:
            k = "other"
            enum_types[ty] += 1
        kind[k] += 1
        head = t[max(0, m.start() - 400):m.start()]
        items = list(ITEM.finditer(head))
        it = items[-1].group(1) if items else "?"
        site[it] += 1
        key = (f, m.start() - 400 + (items[-1].start() if items else 0))
        items_with.add(key)
        params_per_item[key] += 1
        if len(examples[(it, k.split(':')[0])]) < 4:
            line = t.count("\n", 0, m.start()) + 1
            examples[(it, k.split(':')[0])].append(f"{os.path.relpath(f, ROOT)}:{line}: {t[m.start()-60:m.end()+20].strip()!r}")
        if it == "fn":
            fn_params += 1
            b = body_after(t, m.end())
            n = re.escape(name)
            if re.search(r"\b(if|while|&&|\|\|)\s*!?\s*\(?\s*" + n + r"\b|\b" + n + r"\s*(&&|\|\|)|match\s+" + n + r"\b|\b" + n + r"\s*(==|!=)", b):
                use["branch (if/match/&&/==)"] += 1
            if re.search(r";\s*\{?\s*" + n + r"\b[^\]]*\]", b) or re.search(r"\[[^\[\];]*;\s*\{?\s*" + n, b):
                use["array length [T; N]"] += 1
            if re.search(r"\b" + n + r"\s*(\+|-|\*|/|%|<<|>>|as\b)|(\+|-|\*|/|%)\s*" + n + r"\b", b):
                use["arithmetic or `as`"] += 1
            if re.search(r"(::<|<)[^<>;(){}]*\{?\s*!?\s*" + n + r"\s*\}?[^<>;(){}]*>", b):
                use["passed on as a const argument"] += 1
            if re.search(r"\b" + n + r"\b", b) is None:
                use["not named in the body"] += 1

# Call sites: turbofish and type arguments that hold const arguments.
arg_kind = collections.Counter()
GENARGS = re.compile(r"(::<|\b[A-Z][A-Za-z0-9_]*<)([^<>;]{1,200})>")
for f, t in texts.items():
    for m in GENARGS.finditer(t):
        for a in m.group(2).split(","):
            a = a.strip()
            if a in ("true", "false"):
                arg_kind["bool literal"] += 1
            elif re.fullmatch(r"\d[\d_]*(usize|u8|u16|u32|u64|i32)?", a):
                arg_kind["integer literal"] += 1
            elif a.startswith("{") and a.endswith("}"):
                inner = a[1:-1].strip()
                if inner.lstrip("!").strip() in param_names:
                    arg_kind["{ another const parameter } (maybe negated)"] += 1
                else:
                    arg_kind["{ expression block }"] += 1
            elif re.fullmatch(r"[A-Z][A-Za-z0-9_]*::[A-Z][A-Za-z0-9_]*", a) and a.split("::")[0] in {x.split("::")[-1] for x in enum_types}:
                arg_kind["enum variant path"] += 1
            elif re.fullmatch(r"[A-Z][A-Z0-9_]+", a):
                if a in param_names:
                    arg_kind["const parameter name (or ALL_CAPS const)"] += 1
                else:
                    arg_kind["other ALL_CAPS const"] += 1

for f, t in texts.items():
    gce += len(re.findall(r"\{\s*[A-Z_][A-Z0-9_]*\s*[\+\-\*/]\s*[A-Z0-9_]+\s*\}", t))

print("files", len(files))
print("const generic parameters", total, "in items", len(items_with))
print("by kind", dict(kind))
print("by item kind", dict(site))
print("other types", enum_types.most_common(25))
print("params per item", collections.Counter(params_per_item.values()))
print("fn params", fn_params, "uses", dict(use))
print("const fn", const_fn, const_fn_files.most_common(12))
print("call-site const args", dict(arg_kind))
print("generic_const_exprs-like {A op B} args", gce)
for k, v in sorted(examples.items()):
    print(k)
    for e in v:
        print("   ", e[:230])
