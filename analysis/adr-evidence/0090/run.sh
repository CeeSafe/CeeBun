#!/bin/bash
# ADR 0090's evidence: runs every probe and benchmark, and prints what the ADR quotes.
# usage: bash analysis/adr-evidence/0090/run.sh [ceesafec] [upstream]   (from the repository's root)
here="$(cd "$(dirname "$0")" && pwd)"
C="${1:-$HOME/dev/CeeSafe/out/ceesafec}"
UP="${2:-$here/../../../upstream}"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
echo "== compiler: $("$C" --version)"
for p in p1_into_raw p2_spare; do echo "== $p (check)"; "$C" check "$here/$p.cee" 2>&1 | grep 'error\['; done
for p in p3_resize_then_truncate p4_spare_pointer p6_append_today; do echo "== $p (run --interp)"; "$C" run --interp "$here/$p.cee" 2>&1; done
echo "== p5_parts_export (check)"; (cd "$here/p5_parts_export" && "$C" check 2>&1 | grep 'error\[')
for b in b_resize b_reserve; do
  "$C" build "$here/$b.cee" -o "$work/$b" >/dev/null 2>&1
  echo "== $b (200 buffers of 16 MiB)"; ( time -p "$work/$b" ) 2>&1 | tr '\n' ' '; echo
done
echo "== buffers.py"; python3 -I "$here/buffers.py" "$UP"
