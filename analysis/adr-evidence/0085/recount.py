"""Recount arms, guards and matches! (balanced, multi-line) in Bun's src.
Usage: python3 -I recount.py <upstream>
Reports two file sets: all of src/, and src/ without directories named test, tests or testing."""
import os, re, sys, importlib.util

root = sys.argv[1]
TESTDIRS = {'test', 'tests', 'testing'}

def strip_comment(line):
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

def matches_calls(text):
    """Yield the argument text of every matches!( ... ) with balanced brackets."""
    for m in re.finditer(r'\bmatches!\s*\(', text):
        i = m.end(); depth = 1; start = i; q = False
        while i < len(text) and depth:
            ch = text[i]
            if q:
                if ch == '\\': i += 1
                elif ch == '"': q = False
            elif ch == '"': q = True
            elif ch in '([{': depth += 1
            elif ch in ')]}': depth -= 1
            i += 1
        yield text[start:i-1]

def has_guard(args):
    depth = 0; seen_comma = False
    for m in re.finditer(r'[\(\[\{\)\]\}]|,|\bif\b', args):
        t = m.group(0)
        if t in '([{': depth += 1
        elif t in ')]}': depth -= 1
        elif depth == 0 and t == ',': seen_comma = True
        elif depth == 0 and t == 'if' and seen_comma: return True
    return False

res = {'all': [0]*6, 'no-test-dirs': [0]*6}  # files, arms, guards, matches lines, matches calls, matches guard
for dp, dn, fn in os.walk(os.path.join(root, 'src')):
    rel_parts = os.path.relpath(dp, root).split(os.sep)
    is_test = any(p in TESTDIRS for p in rel_parts)
    for f in fn:
        if not f.endswith('.rs'): continue
        try:
            raw = open(os.path.join(dp, f), encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        lines = [strip_comment(l) for l in raw.split('\n')]
        arms = guards = mlines = 0
        for s in (l.strip() for l in lines):
            if not s: continue
            m = re.match(r'^(.*?)\s=>(\s|$)', s)
            if m and '$' not in m.group(1):
                head = m.group(1)
                if not re.search(r'(?<![=!<>.])=(?![=>])', head):
                    arms += 1
                    if top_level_has(head, r'\bif\b') or s.startswith('if '): guards += 1
            if 'matches!(' in s: mlines += 1
        text = '\n'.join(lines)
        calls = list(matches_calls(text))
        mg = sum(1 for a in calls if has_guard(a))
        for key in (['all'] if is_test else ['all', 'no-test-dirs']):
            r = res[key]
            r[0] += 1; r[1] += arms; r[2] += guards; r[3] += mlines; r[4] += len(calls); r[5] += mg
for k, r in res.items():
    print(f"{k}: files {r[0]} arms {r[1]} guards {r[2]} matches!-lines {r[3]} matches!-calls {r[4]} matches!-with-guard {r[5]}")
