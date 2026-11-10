#!/bin/bash
# ADR 0088 probe (§1.11): what the host's compiler flags reach, and whether CeeSafe can join the host's LTO.
# (1) --cflag reaches the runtime: --emit obj with -fsanitize=address, then a runtime function's code is read.
# (2) --emit obj with -flto=thin: the -r step runs LTO, so the result is native code, not bitcode.
# (3) An archive of bitcode members (each C file of --emit c compiled with -flto=thin): the host's LTO link takes it.
cd "$(dirname "$0")"
C=${CEESAFEC:-$HOME/dev/CeeSafe/out/ceesafec}
rm -rf out && mkdir out
A=../g8/alpha
(cd $A && "$C" build --emit obj --offline -o ../../lto/out/plain.o)
(cd $A && "$C" build --emit obj --offline --cflag -fsanitize=address -o ../../lto/out/asan.o)
for o in plain asan; do   # ASan's checks are inline: shadow address (lsr #3) and calls to __asan_report_*
    echo "--emit obj ($o): the runtime's ceesafe_scratch_enter_root has" \
        "$(objdump -d --disassemble-symbols=_ceesafe_scratch_enter_root out/$o.o | grep -cE 'lsr.*#(0x)?3$') shadow loads"
done
(cd $A && "$C" build --emit obj --offline --cflag -flto=thin -o ../../lto/out/thin.o)
echo "--emit obj --cflag -flto=thin: $(file -b out/thin.o | cut -d, -f1)"
(cd $A && "$C" build --emit c --offline -o ../../lto/out/c)
for f in out/c/*.c; do clang -std=c11 -O2 -flto=thin -Iout/c -c "$f" -o "${f%.c}.o"; done
echo "a member compiled with -flto=thin: $(file -b out/c/main.o | cut -d, -f1)"
rm -f out/libalpha.a && ar rcs out/libalpha.a out/c/*.o
clang -O2 -flto=thin host.c out/libalpha.a -o out/host && ./out/host
