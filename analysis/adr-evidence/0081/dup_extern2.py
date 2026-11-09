import os, re, sys, collections
root = sys.argv[1]
# name -> list of (crate, file, normalized signature)
decl = collections.defaultdict(list)
fnre = re.compile(r'^\s*(?:pub(?:\([^)]*\))?\s+)?(?:safe\s+|unsafe\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)')
def norm(sig):
    sig = re.sub(r'\s+', ' ', sig)
    sig = re.sub(r'\b[a-z_][a-z0-9_]*\s*:', ':', sig)       # drop parameter names
    sig = re.sub(r'^\s*pub(\([^)]*\))?\s+', '', sig)
    sig = re.sub(r'^(safe|unsafe)\s+', '', sig)
    sig = sig.replace('core::ffi::', '').replace('std::ffi::', '').replace('libc::', '').replace('ffi::', '')
    return sig.strip().rstrip(';').strip()
for dp, dn, fn in os.walk(os.path.join(root, 'src')):
    for f in fn:
        if not f.endswith('.rs'): continue
        p = os.path.join(dp, f)
        d = dp
        while d != root and not os.path.exists(os.path.join(d, 'Cargo.toml')): d = os.path.dirname(d)
        crate = os.path.relpath(d, root)
        lines = open(p, errors='replace').read().split('\n')
        inext = False; depth = 0; i = 0
        while i < len(lines):
            line = lines[i]; s = line.strip()
            if not inext and re.match(r'^(?:unsafe\s+)?extern\s+"C(?:-unwind)?"\s*\{', s):
                inext = True; depth = 0
            if inext:
                m = fnre.match(line)
                if m:
                    sig = line; j = i
                    while ';' not in sig and j + 1 < len(lines): j += 1; sig += ' ' + lines[j]
                    decl[m.group(1)].append((crate, os.path.relpath(p, root), norm(sig.split(';')[0])))
                depth += line.count('{') - line.count('}')
                if depth <= 0: inext = False
            i += 1
multi_crate = {k: v for k, v in decl.items() if len({c for c, _, _ in v}) > 1}
same_crate = {k: v for k, v in decl.items() if any(n > 1 for n in collections.Counter(c for c, _, _ in v).values())}
differ = {k: v for k, v in multi_crate.items() if len({s for _, _, s in v}) > 1}
print('extern fns:', len(decl), '| declared in >1 crate:', len(multi_crate), '| >1 file of one crate:', len(same_crate), '| cross-crate with differing text:', len(differ))
prefix = collections.Counter((re.match(r'_*[A-Za-z]+', k).group(0).lstrip('_')) for k in multi_crate)
print('by prefix:', prefix.most_common(10))
for k, v in list(differ.items())[:5]:
    print('DIFF', k); [print('   ', c, '|', s) for c, _, s in v]
for k, v in list(same_crate.items())[:3]:
    print('SAME-CRATE', k, [f for _, f, _ in v])
