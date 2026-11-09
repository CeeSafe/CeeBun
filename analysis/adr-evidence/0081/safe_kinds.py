"""ADR 0081: the `safe fn` declarations inside `extern "C"` blocks, by what they take (python3 -I safe_kinds.py upstream)."""
import os, re, sys, collections
root = sys.argv[1]
fnre = re.compile(r'^\s*(?:pub(?:\([^)]*\))?\s+)?(safe\s+|unsafe\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)')
kinds = collections.Counter()
for dp, dn, fn in os.walk(os.path.join(root, 'src')):
    for f in fn:
        if not f.endswith('.rs'):
            continue
        lines = open(os.path.join(dp, f), errors='replace').read().split('\n')
        inext = False; depth = 0
        for i, line in enumerate(lines):
            if not inext and re.match(r'^(?:unsafe\s+)?extern\s+"C(?:-unwind)?"\s*\{', line.strip()):
                inext = True; depth = 0
            if inext:
                m = fnre.match(line)
                if m and (m.group(1) or '').strip() == 'safe':
                    sig = line; j = i
                    while ';' not in sig and j + 1 < len(lines):
                        j += 1; sig += ' ' + lines[j]
                    params = sig.split(';')[0]
                    params = params[params.find('('):]
                    kinds['pointer or reference' if ('*' in params or '&' in params)
                          else 'JSValue by value' if 'JSValue' in params else 'plain values only'] += 1
                depth += line.count('{') - line.count('}')
                if depth <= 0:
                    inext = False
print(sum(kinds.values()), dict(kinds))
