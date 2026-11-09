import os, sys, collections
root = sys.argv[1]
tomls = set(); rs = []
for d, ds, fs in os.walk(root):
    ds[:] = [x for x in ds if x not in ('.git','node_modules','target','vendor')]
    if 'Cargo.toml' in fs: tomls.add(d)
    rs += [os.path.join(d,f) for f in fs if f.endswith('.rs')]
def crate(p):
    d = os.path.dirname(p)
    while d.startswith(root) and d not in tomls: d = os.path.dirname(d)
    return d
by = collections.defaultdict(list)
for p in rs: by[crate(p)].append(p)
by = {c:v for c,v in by.items() if c in tomls and c != root}
print("Cargo.toml dirs", len(tomls), "crates with .rs", len(by), "rs files", sum(len(v) for v in by.values()))
sizes = sorted(len(v) for v in by.values())
print("files per crate: median", sizes[len(sizes)//2], "max", sizes[-1])
big = sorted(by.items(), key=lambda kv: -len(kv[1]))[:4]
for c,v in big: print(os.path.relpath(c, root), len(v))
stems = collections.Counter(os.path.basename(p) for v in by.values() for p in v)
print("basenames in >1 file", sum(1 for n in stems.values() if n>1), "files with a shared basename", sum(n for n in stems.values() if n>1))
# would stem+crate collide?
k = collections.Counter((c, os.path.basename(p)) for c,v in by.items() for p in v)
print("within-crate basename clashes (files)", sum(n for n in k.values() if n>1))
