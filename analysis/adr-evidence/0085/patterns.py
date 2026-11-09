"""Count Rust pattern forms in Bun's source. Usage: python3 -I patterns.py <upstream> [--examples KIND]"""
import os, re, sys, collections

root = sys.argv[1]
want = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--examples" else None

def strip_comment(line):
    # remove a // comment that is not inside a string (approximate: count quotes before it)
    out, q, i = [], False, 0
    while i < len(line):
        ch = line[i]
        if ch == '\\' and q:
            out.append(line[i:i+2]); i += 2; continue
        if ch == '"':
            q = not q
        if not q and line.startswith('//', i):
            break
        out.append(ch); i += 1
    return ''.join(out)

def top_level_has(s, word_re):
    depth = 0
    for m in re.finditer(r'[\(\[\{\)\]\}]|' + word_re, s):
        t = m.group(0)
        if t in '([{': depth += 1
        elif t in ')]}': depth -= 1
        elif depth == 0: return True
    return False

C = collections.Counter()
ex = collections.defaultdict(list)
guard_kinds = collections.Counter()
files = 0
lines_total = 0

def note(kind, path, n, text):
    C[kind] += 1
    if len(ex[kind]) < 40:
        ex[kind].append(f"{path}:{n}: {text.strip()[:150]}")

for dp, dn, fn in os.walk(os.path.join(root, 'src')):
    for f in fn:
        if not f.endswith('.rs'): continue
        p = os.path.join(dp, f); rel = os.path.relpath(p, root)
        files += 1
        try:
            src = open(p, encoding='utf-8', errors='replace').read().split('\n')
        except OSError:
            continue
        prev = ''
        for n, raw in enumerate(src, 1):
            lines_total += 1
            line = strip_comment(raw)
            s = line.strip()
            if not s: continue
            # arm heads: "PAT =>" with no macro_rules metavariables
            m = re.match(r'^(.*?)\s=>(\s|$)', s)
            is_arm = False
            if m and '$' not in m.group(1):
                head = m.group(1)
                if not re.search(r'(?<![=!<>.])=(?![=>])', head):
                    is_arm = True
            if is_arm:
                note('arm', rel, n, s)
                if re.match(r'^\(', head) and ',' in head: note('tuple_arm', rel, n, s)
                if top_level_has(head, r'\bif\b') or s.startswith('if '):
                    note('guard', rel, n, s)
                    g = head.split(' if ', 1)[1] if ' if ' in head else head[3:]
                    pat = head.split(' if ', 1)[0] if ' if ' in head else prev
                    if re.fullmatch(r'_|[a-z_][a-z0-9_]*', pat.strip()): note('guard_bare', rel, n, s)
                    area = rel.split('/')[1] if '/' in rel else rel
                    C['guard_area:' + area] += 1
                    if re.search(r'lex|pars|token|scan', rel): note('guard_lexparse', rel, n, s)
                    if re.search(r'\b[a-z_]\w*\s*=(?!=)[^=]|\+=|-=|\.push\(|\.take\(\)|\.insert\(', g): note('guard_side_effect', rel, n, s)
                    if 'matches!' in g: guard_kinds['matches!'] += 1
                    elif re.search(r'\.(is_|contains|starts_with|ends_with|eq_ignore|len\(\)|is_empty)', g): guard_kinds['method test (is_*/contains/starts_with/len)'] += 1
                    elif re.search(r'==|!=', g): guard_kinds['equality'] += 1
                    elif re.search(r'<|>', g): guard_kinds['ordering'] += 1
                    elif re.search(r'\w\(', g): guard_kinds['other call'] += 1
                    else: guard_kinds['flag/other'] += 1
                    if '&mut' in g or 'ref mut' in head or '.borrow_mut' in g: note('guard_mut', rel, n, s)
                    if re.search(r'\w+\(\s*\)', g) and not re.search(r'\.(is_|len|is_empty)', g): pass
                if top_level_has(head, r'(?<!\|)\|(?!\|)') or s.startswith('| '):
                    note('or_arm', rel, n, s)
                if '..=' in head or re.search(r"'\s*\.\.\s*'", head): note('range_arm', rel, n, s)
                if re.search(r"b'(\\.|[^'])'", head): note('byte_char_arm', rel, n, s)
                if re.search(r'\b\w+ @ ', head): note('at_arm', rel, n, s)
                if re.match(r'&?\[', head) or re.search(r'\(\s*&?\[|\b(Some|Ok|Err)\(&?\[', head): note('slice_arm', rel, n, s)
                if re.search(r'b"', head): note('bytestr_arm', rel, n, s)
                elif re.search(r'(^|[\s|(])"', head): note('str_arm', rel, n, s)
                if re.search(r'\b[A-Z]\w*(::\w+)*\s*\{', head): note('struct_arm', rel, n, s)
                if re.search(r'\b[A-Z][A-Z0-9_]{2,}\b', head) and not re.search(r'::[A-Z][A-Z0-9_]+\b', head) is None: pass
            if re.search(r'\bmatch\b\s+[^=;]*\{\s*$', s): note('match', rel, n, s)
            if re.search(r'\blet\b[^;=]*=[^;]*\belse\s*\{', s) and not re.search(r'\bif\b', s.split('=')[0]): note('let_else', rel, n, s)
            if re.search(r'\bif\s+let\b', s): note('if_let', rel, n, s)
            if re.search(r'\bwhile\s+let\b', s): note('while_let', rel, n, s)
            if re.search(r'&&\s*let\b', s) or (re.match(r'^&&\s*let\b', s)): note('let_chain', rel, n, s)
            if 'matches!(' in s: note('matches_macro', rel, n, s)
            if re.search(r'matches!\([^,]*,.*\bif\b', s): note('matches_guard', rel, n, s)
            if re.search(r'\bif\s+let\b.*\|', s) and '||' not in s and not re.search(r'\|\w*\|', s): note('if_let_or', rel, n, s)
            if re.search(r'\b(if|while)\s+let\s+&?\[', s) or re.search(r'\blet\s+&?\[[^\]]*\]\s*=', s): note('slice_let', rel, n, s)
            prev = s

print(f"files {files} lines {lines_total}")
for k in ['match','arm','guard','guard_mut','guard_bare','guard_lexparse','guard_side_effect','tuple_arm','or_arm','range_arm','byte_char_arm','at_arm','slice_arm','slice_let','bytestr_arm','str_arm','struct_arm','let_else','if_let','while_let','let_chain','matches_macro','matches_guard','if_let_or']:
    print(f"{k:16} {C[k]}")
print("guard kinds:", dict(guard_kinds))
print(sorted([(v,k) for k,v in C.items() if k.startswith("guard_area:")], reverse=True)[:15])
if want == "all":
    for k in ex:
        print("=== " + k)
        for e in ex[k]: print(e)
elif want:
    for e in ex[want]: print(e)
