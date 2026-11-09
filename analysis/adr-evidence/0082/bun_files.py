import os, sys, collections, re
root = sys.argv[1]
crates = []
for d, ds, fs in os.walk(root):
    ds[:] = [x for x in ds if x not in ('.git','node_modules','target','vendor')]
    if 'Cargo.toml' in fs and os.path.isdir(os.path.join(d,'src')):
        crates.append(d)
crates.sort()
files = []
for c in crates:
    for d, ds, fs in os.walk(os.path.join(c,'src')):
        for f in fs:
            if f.endswith('.rs'):
                files.append((c, os.path.join(d,f)))
stems = collections.Counter(os.path.basename(p) for _, p in files)
dup = sum(n for s,n in stems.items() if n>1)
print("crates", len(crates), "rs files", len(files), "distinct basenames", len(stems), "files sharing a basename", dup)
print("top", stems.most_common(8))
# distinct basenames per crate collisions across crates
rel = collections.Counter((os.path.relpath(p, c)) for c,p in files)
print("files whose path within crate is shared with another crate", sum(n for s,n in rel.items() if n>1))
inl = generic_fn = pubfn = 0
for _, p in files:
    t = open(p, encoding='utf-8', errors='replace').read()
    inl += len(re.findall(r'#\[inline(\(always\))?\]', t))
    generic_fn += len(re.findall(r'\bfn\s+\w+\s*<', t))
    pubfn += len(re.findall(r'\bpub(\([^)]*\))?\s+(const\s+|unsafe\s+|extern\s+"C"\s+)*fn\b', t))
print("inline attrs", inl, "generic fns", generic_fn, "pub fns", pubfn)
