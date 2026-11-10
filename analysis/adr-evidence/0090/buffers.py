#!/usr/bin/env python3
"""ADR 0090's counts: how Bun's Rust moves a buffer's ownership through raw parts, and writes into spare capacity.

usage: python3 -I analysis/adr-evidence/0090/buffers.py upstream

Counts occurrences in hand-written Rust under src/ (comments and string literals are not stripped; the patterns are
method and path names that rarely occur in either), per pattern and per top-level directory.
"""
import os, re, sys
from collections import Counter

ROOT = sys.argv[1]
PATTERNS = [
    ("Vec::from_raw_parts", r"\bVec::(?:<[^>]*>::)?from_raw_parts(?:_in)?\b"),
    ("into_raw_parts / ManuallyDrop<Vec>", r"\binto_raw_parts(?:_with_alloc)?\b|ManuallyDrop::new\(\s*(?:vec|v|buf|list|out|bytes)\b"),
    ("mem::forget", r"\bmem::forget\b|\bcore::mem::forget\b"),
    ("Box::into_raw", r"\bBox::into_raw\b|\bheap::into_raw\b"),
    ("Box::from_raw", r"\bBox::from_raw\b|\bheap::take\b|\bheap::destroy\b"),
    ("Box::leak / Vec::leak", r"\bBox::leak\b|\.leak\(\)"),
    ("into_boxed_slice", r"\binto_boxed_slice\b"),
    ("spare_capacity_mut", r"\bspare_capacity_mut\b"),
    ("set_len", r"\.set_len\("),
    ("commit_spare", r"\bcommit_spare\b"),
    ("as_mut_ptr on a call's argument", r"\.as_mut_ptr\(\)"),
    ("slice::from_raw_parts(_mut)", r"\bslice::from_raw_parts(?:_mut)?\b|\bffi::slice(?:_mut)?\("),
    ("try_reserve(_exact)", r"\.try_reserve(?:_exact)?\("),
]
total = Counter(); by_dir = {name: Counter() for name, _ in PATTERNS}; files = 0
for d, _, fs in os.walk(os.path.join(ROOT, "src")):
    for f in fs:
        if not f.endswith(".rs"): continue
        files += 1
        text = open(os.path.join(d, f), errors="replace").read()
        top = os.path.relpath(d, os.path.join(ROOT, "src")).split(os.sep)[0]
        for name, pat in PATTERNS:
            n = len(re.findall(pat, text))
            if n: total[name] += n; by_dir[name][top] += n
print(f"files {files}")
for name, _ in PATTERNS:
    top = ", ".join(f"{k} {v}" for k, v in by_dir[name].most_common(6))
    print(f"{name:36} {total[name]:6}   {top}")
