"""Byte-string and string literal arms in Bun's src/, outside map macros (name ending in _map! or map!)."""
import os, re, sys
root = sys.argv[1]; bs = st = inmac = 0; mac_lines = 0; ex = []
for dp, dn, fn in os.walk(os.path.join(root, 'src')):
    for f in fn:
        if not f.endswith('.rs'): continue
        p = os.path.join(dp, f); depth = 0; inm = False
        for n, line in enumerate(open(p, encoding='utf-8', errors='replace'), 1):
            s = line.strip()
            if not inm and re.search(r'\w*map!\s*[\{\(\[]', s):
                inm = True; depth = 0
            if inm:
                depth += s.count('{') + s.count('(') + s.count('[') - s.count('}') - s.count(')') - s.count(']')
                if re.match(r'^b?"', s) and '=>' in s: mac_lines += 1
                if depth <= 0 and not re.search(r'map!\s*[\{\(\[]\s*$', s): inm = False
                continue
            m = re.match(r'^(\|\s*)?((Some\(|Ok\(|\(|\[)?\s*b"[^"]*")', s)
            if m and ('=>' in s or s.endswith('|')): bs += 1; len(ex) < 6 and n % 4 == 0 and ex.append(f"{os.path.relpath(p, root)}:{n}: {s[:120]}")
            elif re.match(r'^(\|\s*)?(Some\()?"[^"]*"\s*(\||=>|if)', s): st += 1
print("bytestr arms", bs, "str arms", st, "map-macro entries", mac_lines)
print("\n".join(ex))
