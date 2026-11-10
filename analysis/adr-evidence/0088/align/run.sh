#!/bin/bash
# ADR 0088 probe (§1.9): a host allocator that keeps malloc's contract as written ("aligned for max_align_t", 8 on
# macOS arm64) but never returns 16-aligned blocks. The runtime's platform functions are renamed out of the way, so
# align8.c's take their place, and a program with async tasks (cee_task is _Alignas(16)) runs under UBSan.
cd "$(dirname "$0")"
C=${CEESAFEC:-$HOME/dev/CeeSafe/out/ceesafec}
rm -rf out && mkdir out
"$C" build --emit c async-scope.cee -o out/c >/dev/null
echo "max_align_t here: $(printf '#include <stddef.h>\n#include <stdio.h>\nint main(void){printf("%%zu",_Alignof(max_align_t));}' \
    | clang -x c - -o out/ma && ./out/ma)"
R="-Dceesafe_platform_alloc=unused_alloc -Dceesafe_platform_alloc_zeroed=unused_alloc_zeroed"
R="$R -Dceesafe_platform_realloc=unused_realloc -Dceesafe_platform_free=unused_free"
F="-std=c11 -g -O1 -fsanitize=alignment -fno-sanitize-recover=alignment -Iout/c"
for f in out/c/*.c; do
    case $f in *ceesafe_rt_hosted.c) clang $F $R -c "$f" -o "$f.o" ;; *) clang $F -c "$f" -o "$f.o" ;; esac
done
clang $F align8.c out/c/*.o -o out/prog
./out/prog > out/log 2>&1; echo "status=$?"
grep -m1 'runtime error' out/log | sed 's/^.*runtime error/runtime error/'
