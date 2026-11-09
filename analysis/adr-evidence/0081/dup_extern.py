import os, re, sys, collections
root = sys.argv[1]
# crate = directory holding the nearest Cargo.toml
decl = collections.defaultdict(set)
fnre = re.compile(r'^\s*(?:pub(?:\([^)]*\))?\s+)?(?:safe\s+|unsafe\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)')
for dp, dn, fn in os.walk(os.path.join(root, 'src')):
    for f in fn:
        if not f.endswith('.rs'): continue
        p = os.path.join(dp, f)
        d = dp
        while d != root and not os.path.exists(os.path.join(d, 'Cargo.toml')): d = os.path.dirname(d)
        crate = os.path.relpath(d, root)
        depth = 0; inext = False
        for line in open(p, errors='replace'):
            s = line.strip()
            if not inext and re.match(r'^(?:unsafe\s+)?extern\s+"C(?:-unwind)?"\s*\{', s):
                inext = True; depth = 0
            if inext:
                m = fnre.match(line)
                if m: decl[m.group(1)].add(crate)
                depth += line.count('{') - line.count('}')
                if depth <= 0: inext = False
multi = {k: v for k, v in decl.items() if len(v) > 1}
print('extern fns declared:', len(decl), ' in >1 crate:', len(multi), ' redundant declarations:', sum(len(v)-1 for v in multi.values()))
for k, v in sorted(multi.items(), key=lambda kv: -len(kv[1]))[:12]: print(f'  {k}: {len(v)} crates')
