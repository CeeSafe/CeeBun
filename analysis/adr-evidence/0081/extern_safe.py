import os, re, sys, collections
root = sys.argv[1]
fnre = re.compile(r'^\s*(?:pub(?:\([^)]*\))?\s+)?(safe\s+|unsafe\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)')
kinds = collections.Counter(); refs = 0; total = 0; safe_names = set(); blocks = collections.Counter()
for dp, dn, fn in os.walk(os.path.join(root, 'src')):
    for f in fn:
        if not f.endswith('.rs'): continue
        lines = open(os.path.join(dp, f), errors='replace').read().split('\n')
        inext = False; depth = 0
        for i, line in enumerate(lines):
            s = line.strip()
            m0 = re.match(r'^(unsafe\s+)?extern\s+"C(?:-unwind)?"\s*\{', s)
            if not inext and m0:
                inext = True; depth = 0; blocks['unsafe extern' if m0.group(1) else 'extern'] += 1
            if inext:
                m = fnre.match(line)
                if m:
                    total += 1
                    kinds[(m.group(1) or 'plain').strip()] += 1
                    sig = line; j = i
                    while ';' not in sig and j + 1 < len(lines): j += 1; sig += lines[j]
                    if re.search(r'[(,:]\s*&', sig.split(';')[0]): refs += 1
                    if m.group(1) and m.group(1).strip() == 'safe': safe_names.add(m.group(2))
                depth += line.count('{') - line.count('}')
                if depth <= 0: inext = False
print('extern fn declarations:', total, dict(kinds), '| with & references in the signature:', refs, '| blocks:', dict(blocks))
# call sites of safe fns outside extern blocks (rough: name followed by '(')
calls = 0
pat = re.compile(r'\b(' + '|'.join(sorted(safe_names, key=len, reverse=True)[:4000]) + r')\s*\(') if safe_names else None
for dp, dn, fn in os.walk(os.path.join(root, 'src')):
    for f in fn:
        if f.endswith('.rs') and pat:
            for line in open(os.path.join(dp, f), errors='replace'):
                if 'fn ' in line: continue
                calls += len(pat.findall(line))
print('distinct safe fns:', len(safe_names), '| rough call sites of them:', calls)
