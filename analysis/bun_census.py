"""Census of a Bun source tree: lines of code by language and by top-level area, without blank lines and comment-only
lines (a rough filter: `//`, `/*`, `*`, `#` for scripts). Reports what is first-party source versus tests, vendored
code and generated code, and the Rust crates of the workspace."""
import collections, os, re, sys

ROOT = sys.argv[1]
LANG = {".rs": "Rust", ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++", ".hh": "C++", ".h": "C/C++ header",
        ".c": "C", ".zig": "Zig", ".ts": "TypeScript", ".mts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript",
        ".mjs": "JavaScript", ".cjs": "JavaScript", ".py": "Python", ".sh": "Shell", ".S": "Assembly", ".s": "Assembly"}
SKIP_DIRS = {".git", "node_modules", "target"}


def kind(rel):
    p = rel.split(os.sep)
    if p[0] == "test" or "test" in p or "tests" in p or "__tests__" in p or rel.endswith((".test.ts", ".test.js")):
        return "tests"
    if any(x in ("vendor", "third_party", "deps", "thirdparty") for x in p):
        return "vendored"
    if any(x in ("generated", "codegen-out") for x in p) or "/generated" in rel:
        return "generated"
    if p[0] in ("bench", "docs", "misctools", "scripts", "tools", "dockerhub", "completions"):
        return "tooling/docs"
    return "source"


def sloc(path):
    n = 0
    try:
        with open(path, errors="replace") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith(("//", "/*", "*", "*/")):
                    continue
                n += 1
    except OSError:
        pass
    return n


by = collections.Counter()
area = collections.Counter()
files = collections.Counter()
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    for fn in filenames:
        ext = os.path.splitext(fn)[1]
        lang = LANG.get(ext)
        if not lang:
            continue
        full = os.path.join(dirpath, fn)
        rel = os.path.relpath(full, ROOT)
        k = kind(rel)
        n = sloc(full)
        by[(k, lang)] += n
        files[(k, lang)] += 1
        if k == "source":
            parts = rel.split(os.sep)
            top = os.sep.join(parts[:2]) if parts[0] in ("src", "packages") and len(parts) > 2 else parts[0]
            area[(top, lang)] += n

print("== lines of code by kind and language (files)")
for (k, lang), n in sorted(by.items(), key=lambda x: (x[0][0], -x[1])):
    if n >= 1000:
        print(f"  {k:13} {lang:15} {n:>10,}  ({files[(k, lang)]:,} files)")

print("\n== first-party source by area (Rust, C++, C, Zig only; areas over 3,000 lines)")
tot = collections.Counter()
for (top, lang), n in area.items():
    if lang in ("Rust", "C++", "C/C++ header", "C", "Zig"):
        tot[top] += n
for top, n in tot.most_common(40):
    if n < 3000:
        break
    parts = ", ".join(f"{lang} {area[(top, lang)]:,}" for lang in ("Rust", "C++", "C/C++ header", "C", "Zig")
                      if area[(top, lang)])
    print(f"  {top:45} {n:>9,}  {parts}")

cargo = os.path.join(ROOT, "Cargo.toml")
if os.path.exists(cargo):
    txt = open(cargo).read()
    m = re.search(r"members\s*=\s*\[(.*?)\]", txt, re.S)
    members = re.findall(r"\"([^\"]+)\"", m.group(1)) if m else []
    print(f"\n== Cargo workspace members: {len(members)}")
    print("  " + ", ".join(members[:80]))
lock = os.path.join(ROOT, "Cargo.lock")
if os.path.exists(lock):
    pk = re.findall(r'\[\[package\]\]\nname = "([^"]+)"\nversion = "([^"]+)"\n(source = "([^"]+)")?', open(lock).read())
    ext = [(n, v) for n, v, _, s in pk if s]
    print(f"\n== Cargo.lock: {len(pk)} packages, {len(ext)} from crates.io/git (third-party)")
    print("  " + ", ".join(f"{n} {v}" for n, v in sorted(ext)[:200]))
