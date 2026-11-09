"""matches! with a guard: an `if` at nesting depth 0 after the first top-level comma (the pattern argument)."""
import os, re, runpy, sys

sys.argv = ["shapes.py", sys.argv[1]]
ns = {}
src = open(os.path.expanduser("~/dev/CeeSafeApps/bun/analysis/adr-evidence/0087/shapes.py")).read()
src = src.split("c = collections.Counter()")[0]
exec(compile(src, "shapes.py", "exec"), ns)
total = loose = strict = 0
for _, a in ns["calls"]("matches"):
    total += 1
    if re.search(r"\bif\b", a):
        loose += 1
    depth, comma, buf = 0, False, []
    for ch in a:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if depth == 0 and ch == "," and not comma:
            comma = True
            continue
        buf.append(ch if (comma and depth == 0) else " ")
    if re.search(r"\bif\b", "".join(buf)):
        strict += 1
print({"matches": total, "loose": loose, "top-level guard": strict})
