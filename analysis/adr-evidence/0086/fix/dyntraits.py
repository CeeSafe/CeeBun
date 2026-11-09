"""Of Bun's traits used as `dyn Name`, which have members that cannot sit in a table (static fns, Self in a signature,
by-value self, generic methods) and which have default methods. Reuses traits.py's parser."""
import re, sys, collections
sys.argv = [sys.argv[0], sys.argv[1]]
src = open(__file__.replace("dyntraits.py", "traits.py")).read().split("C = collections.Counter()")[0]
exec(src)
TRAIT = re.compile(r"^[ \t]*(?:pub(?:\([^)]*\))?\s+)?(?:unsafe\s+)?trait\s+(\w+)([^{;]*)\{", re.M)
info = {}
alltext = []
for rel, raw in files:
    t = strip(raw); alltext.append(t)
    for m in TRAIT.finditer(t):
        o = m.end() - 1; body = t[o + 1:block(t, o)]
        f = collections.Counter()
        for kind, s, e, txt, has_body in depth1_items(body):
            if kind != "fn": f["k_"+kind] += 1; continue
            sig = txt.split('{')[0] if has_body else txt
            if has_body: f["default"] += 1
            if not re.search(r"\(\s*(&\s*('\w+\s+)?(mut\s+)?)?(mut\s+)?self\b", sig): f["static"] += 1
            elif re.search(r"\(\s*(mut\s+)?self\b", sig): f["byvalue"] += 1
            rest = re.sub(r"&\s*('\w+\s+)?(mut\s+)?self\b", "", sig)
            if re.search(r"\bSelf\b(?!::)", rest): f["Self"] += 1
            if re.match(r"fn\s+\w+\s*<\s*(?!')", sig): f["generic"] += 1
        info[m.group(1)] = f
big = "\n".join(alltext)
used = collections.Counter(re.findall(r"\bdyn\s+(?:\w+::)*(\w+)", big))
dyn_traits = [n for n in info if used[n]]
c = collections.Counter()
for n in dyn_traits:
    f = info[n]; c["dyn-used traits"] += 1
    if f["default"]: c["  with defaults"] += 1
    if any(k.startswith("k_") for k in f): c["  with const/type"] += 1; print("   ", n, dict(f), used[n])
print(dict(c))
