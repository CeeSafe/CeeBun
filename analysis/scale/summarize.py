"""Print analysis/scale/results.jsonl (or the files given) as a Markdown table, one row per run."""

import json
import os
import sys

paths = sys.argv[1:] or [os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.jsonl")]
rows = []
for path in paths:
    with open(path) as f:
        rows += [json.loads(line) for line in f if line.strip()]


def step(r, k):
    s = r.get(k)
    if not s:
        return "–"
    if s["exit"] != 0:
        return f"failed ({s['exit']})"
    return f"{s['seconds']:g} s, {s['rss_mb'] / 1024:.1f} GB" if s["rss_mb"] >= 1024 else f"{s['seconds']:g} s, {s['rss_mb']:.0f} MB"


print("| Host | Compiler | Lines | Packages | check | emit C | C size | build (C compiler included) | Runs |")
print("|---|---|---|---|---|---|---|---|---|")
for r in rows:
    runs = "–"
    if "native_exit" in r:
        runs = "yes" if r["native_exit"] == 0 else f"exit {r['native_exit']}"
        if "differential_ok" in r:
            runs += ", = interpreter" if r["differential_ok"] else ", ≠ interpreter"
    c = f"{r['c_mb']:g} MB" if "c_mb" in r else "–"
    host = r.get("host", "MacBookPro darwin-arm64 8 cpus").split()[0]
    path = r.get("compiler_path", "")
    compiler = "release" if ".ceesafe/bin" in path or "ceesafe-0.24.2" in path else "fixed (fe4d0ca)"
    print(f"| {host} | {compiler} | {r['lines']:,} | {r['packages']} | {step(r, 'check')} | {step(r, 'emit_c')} | {c} | {step(r, 'build')} | {runs} |")
