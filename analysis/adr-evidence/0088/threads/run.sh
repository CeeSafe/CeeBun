#!/bin/bash
# ADR 0088 probe (§1.8): the runtime's per-process state is shared by threads. Safe code only: each call enters a
# root scratch frame. (1) Two threads of one CeeSafe program (Thread.spawn), no embedding. (2) A C host whose two
# pthreads call one export. (3) The same host under ThreadSanitizer, the runtime compiled from --emit c.
cd "$(dirname "$0")"
C=${CEESAFEC:-$HOME/dev/CeeSafe/out/ceesafec}
rm -rf out && mkdir out
"$C" build spawn.cee -o out/spawn && { ./out/spawn 2>&1 | head -1; echo "spawn status=${PIPESTATUS[0]}"; }
(cd scr && "$C" build --emit obj --offline -o ../out/scr.o)
clang host.c out/scr.o -o out/host && { ./out/host 2>&1 | head -1; echo "host status=${PIPESTATUS[0]}"; }
(cd scr && "$C" build --emit c --offline -o ../out/scr_c)
clang -std=c11 -g -O1 -fsanitize=thread -Iout/scr_c host.c out/scr_c/*.c -o out/host_tsan 2>/dev/null \
    && TSAN_OPTIONS=halt_on_error=1 ./out/host_tsan 2>&1 | grep -E '^SUMMARY' | head -1
