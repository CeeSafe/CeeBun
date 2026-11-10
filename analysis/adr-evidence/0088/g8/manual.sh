#!/bin/sh
# ADR 0088 probe: the library mode done by hand with today's compiler. Each package's main.c (from --emit c) is
# compiled alone, the runtime once (beta's, which has the thread layer alpha lacks), and all are linked with the host.
# It links and runs: the generated code's own functions are static, so only the runtime clashed.
set -e
cd "$(dirname "$0")"
C=${CEESAFEC:-$HOME/dev/CeeSafe/out/ceesafec}
(cd alpha && "$C" build --emit c --offline -o ../alpha_c)
(cd beta && "$C" build --emit c --offline -o ../beta_c)
rm -rf manual && mkdir manual
F="-std=c11 -O2 -c"
clang $F -Ialpha_c alpha_c/main.c -o manual/alpha_main.o
clang $F -Ibeta_c beta_c/main.c -o manual/beta_main.o
for r in beta_c/ceesafe_rt_*.c; do clang $F -Ibeta_c "$r" -o "manual/$(basename "$r" .c).o"; done
clang host.c manual/*.o -o manual/two
./manual/two
echo "global symbols of alpha's main.c: $(nm -gU manual/alpha_main.o | awk '{print $3}' | tr '\n' ' ')"
echo "global symbols of beta's main.c: $(nm -gU manual/beta_main.o | awk '{print $3}' | tr '\n' ' ')"
echo "ABI version macro in each main.c: $(grep -c 'CEESAFE_ABI_VERSION != 1' alpha_c/main.c beta_c/main.c | tr '\n' ' ')"
