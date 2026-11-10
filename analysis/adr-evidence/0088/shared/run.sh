#!/bin/sh
# ADR 0088 probe: two builds sharing a dependency, linked by hand with one runtime (as g8/manual.sh does).
# Unsplit, each build has its own static copy of common (and of its static). Split, common's functions are global but
# carry each build's name (ceeF_one_common_bump, ceeF_two_common_bump), so they do not clash either: both forms link
# and run with two copies of common's state, silently.
set -e
cd "$(dirname "$0")"
C=${CEESAFEC:-$HOME/dev/CeeSafe/out/ceesafec}
F="-std=c11 -O2 -c"
rm -rf out && mkdir out
for p in one two; do (cd $p && "$C" build --emit c --offline -o ../out/$p); clang $F -Iout/$p out/$p/main.c -o out/$p.o; done
for r in out/one/ceesafe_rt_*.c; do clang $F -Iout/one "$r" -o "out/$(basename "$r" .c).o"; done
clang host.c out/one.o out/two.o out/ceesafe_rt_*.o -o out/host
./out/host
for p in one two; do (cd $p && "$C" build --emit c --split --offline -o ../out/${p}_split); done
for p in one two; do
    for f in out/${p}_split/c/*/src/lib.c out/${p}_split/ceesafe_instances.c; do
        clang $F -Iout/${p}_split "$f" -o "$f.o"
    done
done
for p in one two; do
    echo "split: global names of common's unit in build $p:" \
        "$(nm -gU out/${p}_split/c/common/src/lib.c.o | awk '{print $3}' | tr '\n' ' ')"
done
clang host.c out/one_split/c/*/src/lib.c.o out/one_split/ceesafe_instances.c.o out/two_split/c/*/src/lib.c.o \
    out/two_split/ceesafe_instances.c.o out/ceesafe_rt_*.o -o out/host_split
printf 'split: '; ./out/host_split
