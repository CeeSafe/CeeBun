"""Bun's supertrait lists: which names appear, and how many traits name a first-party supertrait."""
import re, sys, collections
src = open(__file__.replace("supers.py", "traits.py")).read().split("C = collections.Counter()")[0]
exec(src)
TRAIT = re.compile(r"^[ \t]*(?:pub(?:\([^)]*\))?\s+)?(?:unsafe\s+)?trait\s+(\w+)\s*(<[^{;]*?>)?\s*:([^{;]*?)(\bwhere\b[^{;]*)?\{", re.M)
STD = set("Sized Copy Clone Send Sync Default Eq PartialEq Debug Display Hash Ord PartialOrd Any Unpin Into From AsRef Fn FnMut FnOnce".split())
names = collections.Counter(); user = 0; ex = []
for rel, raw in files:
    t = strip(raw)
    for m in TRAIT.finditer(t):
        parts = [p.strip() for p in re.split(r"\+(?![^<]*>)", m.group(3)) if p.strip()]
        base = [re.sub(r"<.*", "", p).split("::")[-1].strip() for p in parts if not p.startswith("'")]
        for b in base: names[b] += 1
        if any(b not in STD for b in base):
            user += 1
            if len(ex) < 6: ex.append(f"{rel}:{t.count(chr(10),0,m.start())+1} trait {m.group(1)}: {m.group(3).strip()[:60]}")
print("supertrait names:", names.most_common(14))
print("traits with a non-std supertrait:", user)
for e in ex: print("  ", e)
