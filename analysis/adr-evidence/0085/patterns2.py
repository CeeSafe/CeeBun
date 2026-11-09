"""Second pass: classify arm *patterns* (text before a top-level guard) in Bun's src/, split lint vs rest."""
import os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
root = sys.argv[1]
C = collections.Counter()
EX = collections.defaultdict(list)

def strip_comment(line):
    out, q, i = [], False, 0
    while i < len(line):
        ch = line[i]
        if ch == '\\' and q:
            out.append(line[i:i+2]); i += 2; continue
        if ch == '"': q = not q
        if not q and line.startswith('//', i): break
        out.append(ch); i += 1
    return ''.join(out)

def split_guard(head):
    depth = 0
    for m in re.finditer(r'[\(\[\{\)\]\}]|\bif\b', head):
        t = m.group(0)
        if t in '([{': depth += 1
        elif t in ')]}': depth -= 1
        elif depth == 0: return head[:m.start()].strip(), head[m.end():].strip()
    return head.strip(), None

def kinds(pat):
    k = []
    if re.search(r'b"', pat): k.append('bytestr')
    if re.search(r'(^|[\s|(\[,])"', pat): k.append('str')
    if '..=' in pat: k.append('range')
    if re.search(r"b'(\\.|[^'])'", pat): k.append('bytechar')
    if re.search(r'\b\w+ @ ', pat): k.append('at')
    if re.search(r'(^|[\s(,|&])\[', pat): k.append('slice')
    if re.search(r'\b[A-Z]\w*(::\w+)*\s*\{', pat): k.append('struct')
    if re.match(r'^\(', pat) and ',' in pat: k.append('tuple')
    depth = 0; orp = False
    for ch_i, ch in enumerate(pat):
        if ch in '([{': depth += 1
        elif ch in ')]}': depth -= 1
        elif ch == '|' and pat[ch_i-1:ch_i] != '|' and pat[ch_i+1:ch_i+2] != '|': orp = True
    if orp or pat.startswith('| '): k.append('or')
    if re.search(r'(?<![:\w])[A-Z][A-Z0-9_]{2,}(?![\w(:{])', pat): k.append('const')
    return k

for dp, dn, fn in os.walk(os.path.join(root, 'src')):
    for f in fn:
        if not f.endswith('.rs'): continue
        p = os.path.join(dp, f); rel = os.path.relpath(p, root)
        part = 'lint' if rel.startswith('src/lint/') else 'rest'
        prev = ''
        for n, raw in enumerate(open(p, encoding='utf-8', errors='replace'), 1):
            s = strip_comment(raw).strip()
            if not s: continue
            m = re.match(r'^(.*?)\s=>(\s|$)', s)
            if m and '$' not in m.group(1) and not re.search(r'(?<![=!<>.])=(?![=>])', m.group(1)):
                head = m.group(1)
                if head.startswith('if '):
                    pat, guard = prev, head[3:]
                else:
                    pat, guard = split_guard(head)
                C[(part, 'arm')] += 1
                if guard is not None:
                    C[(part, 'guard')] += 1
                    if re.fullmatch(r'_|[a-z_][a-z0-9_]*', pat): C[(part, 'guard_on_bare')] += 1
                    if re.search(r'&mut\b|\.borrow_mut\(|ref mut', guard + ' ' + pat): C[(part, 'guard_mut')] += 1; EX['guard_mut'].append(f"{rel}:{n}: {s[:160]}")
                    if 'ref ' in pat: C[(part, 'guard_ref')] += 1
                for k in kinds(pat):
                    C[(part, k)] += 1
                    if len(EX[k]) < 12 and part == 'rest' and (n % 3 == 0): EX[k].append(f"{rel}:{n}: {s[:160]}")
            prev = s

names = ['arm','guard','guard_on_bare','guard_mut','guard_ref','or','range','bytechar','bytestr','str','at','slice','struct','tuple','const']
print(f"{'kind':14}{'rest':>8}{'lint':>8}{'all':>8}")
for k in names:
    a, b = C[('rest', k)], C[('lint', k)]
    print(f"{k:14}{a:8}{b:8}{a+b:8}")
for k, v in EX.items():
    print('===', k)
    for e in v[:12]: print(e)
