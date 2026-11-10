#!/bin/sh
# ADR 0088 probe (run after manual.sh): one static archive per build, each with its own copy of the runtime, but one
# archive member per runtime file. The linker takes a member only for a symbol still undefined, so the first archive's
# runtime serves both builds and the second's is never pulled: it links today. It also shows the risk: which copy
# serves is decided by link order, silently, so two compilers' runtimes could mix.
# Then the runtime and generated code compiled with -fvisibility=hidden: a static link still resolves them.
set -e
cd "$(dirname "$0")"
F="-std=c11 -O2 -c"
rm -rf arch && mkdir -p arch/a arch/b
clang $F -Ialpha_c alpha_c/main.c -o arch/a/alpha_main.o
for r in alpha_c/ceesafe_rt_*.c; do clang $F -Ialpha_c "$r" -o "arch/a/$(basename "$r" .c).o"; done
clang $F -Ibeta_c beta_c/main.c -o arch/b/beta_main.o
for r in beta_c/ceesafe_rt_*.c; do clang $F -Ibeta_c "$r" -o "arch/b/$(basename "$r" .c).o"; done
ar rcs arch/liba.a arch/a/*.o
ar rcs arch/libb.a arch/b/*.o
clang host.c arch/liba.a arch/libb.a -o arch/two -Wl,-why_load 2>arch/why_load.txt
./arch/two
echo "members loaded from libb.a: $(grep -o 'libb.a\[[0-9]*\]([a-z_]*.o)' arch/why_load.txt | sort -u | tr '\n' ' ')"
echo "members loaded from liba.a: $(grep -o 'liba.a\[[0-9]*\]([a-z_]*.o)' arch/why_load.txt | sort -u | tr '\n' ' ')"
mkdir -p arch/hidden
for f in alpha_c/main.c beta_c/main.c beta_c/ceesafe_rt_*.c; do
    clang $F -fvisibility=hidden -I"$(dirname "$f")" "$f" -o "arch/hidden/$(echo "$f" | tr / _).o"
done
clang host.c arch/hidden/*.o -o arch/hidden/two && ./arch/hidden/two
