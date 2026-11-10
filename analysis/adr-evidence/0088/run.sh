#!/bin/bash
# ADR 0088's probes, in one run: bash analysis/adr-evidence/0088/run.sh > analysis/adr-evidence/0088/results.txt 2>&1
# Needs bash, ceesafec ($CEESAFEC, default ~/dev/CeeSafe/out/ceesafec), clang, ar, objdump, ld.lld for elf/, and
# rustc for rust_host. macOS (ld64) as measured; on Linux, -Wl,-why_load in g8/archives.sh is -Wl,--trace.
# bun/panic_in_bun.log is the CeeBun trial's output for a deliberate panic (a debug + ASAN Bun), copied, not rerun.
cd "$(dirname "$0")"
C=${CEESAFEC:-$HOME/dev/CeeSafe/out/ceesafec}
echo "== compiler: $("$C" --version); $(clang --version | head -1); $(uname -sm)"

echo "== g8: two packages, each build --emit obj"
(cd g8/alpha && "$C" build --emit obj --offline -o ../alpha.o)
(cd g8/beta && "$C" build --emit obj --offline -o ../beta.o)
for o in alpha beta; do
    echo "$o.o: $(nm -gU g8/$o.o | wc -l | tr -d ' ') global symbols, $(nm -gU g8/$o.o | grep -c ' _ceesafe_') named ceesafe_*;" \
        "others: $(nm -gU g8/$o.o | grep -v ' _ceesafe_' | awk '{print $3}' | tr '\n' ' ')"
done
echo "common (tentative) symbols in alpha.o: $(nm -gU g8/alpha.o | awk '$2 == "C" {print $3}' | tr '\n' ' ')"
echo "in beta.o only: $(comm -13 <(nm -gU g8/alpha.o | awk '{print $3}' | sort) <(nm -gU g8/beta.o | awk '{print $3}' | sort) | tr '\n' ' ')"
echo "-- link both objects:"
clang g8/host.c g8/alpha.o g8/beta.o -o g8/two 2>&1 | grep -E '^ld:|^duplicate symbol' | sed -n '1p;$p'
echo "-- link both as archives (one member each):"
rm -f g8/liba.a g8/libb.a && ar rcs g8/liba.a g8/alpha.o && ar rcs g8/libb.a g8/beta.o
clang g8/host.c g8/liba.a g8/libb.a -o g8/two_ar 2>&1 | grep -E '^ld:|^duplicate symbol' | sed -n '1p;$p'
echo "-- a host defining ceesafe_platform_alloc and ceesafe_panic beside alpha.o, then beside liba.a:"
clang g8/hooks.c g8/alpha.o -o g8/hooks 2>&1 | grep -E '^ld:|^duplicate symbol'
clang g8/hooks.c g8/liba.a -o g8/hooks_ar 2>&1 | grep -E '^ld:|^duplicate symbol'
echo "-- --split: global names other than the runtime's:"
(cd g8/alpha && "$C" build --emit obj --split --offline -o ../alpha_split.o)
nm -gU g8/alpha_split.o | grep -v ' _ceesafe_' | awk '{print $3}' | tr '\n' ' '; echo
echo "-- by hand: each main.c alone, the runtime once (g8/manual.sh):"
sh g8/manual.sh 2>&1 | tail -4
echo "-- by hand: an archive per build with one member per runtime file (g8/archives.sh):"
sh g8/archives.sh 2>&1 | tail -4

echo "== shared: two builds that both depend on the package common (shared/run.sh)"
(cd shared/one && "$C" fetch --offline >/dev/null 2>&1); (cd shared/two && "$C" fetch --offline >/dev/null 2>&1)
sh shared/run.sh 2>&1 | tail -4

echo "== nomain: a C host, no CeeSafe main (nomain/host.c)"
(cd nomain/lib && "$C" build --emit obj --offline -o ../lib.o)
clang nomain/host.c nomain/lib.o -o nomain/host
for init in "" init; do
    for w in boxes leak args panic thread callback; do
        echo "-- host $init $w, CEESAFE_ALLOC_REPORT=1:"
        CEESAFE_ALLOC_REPORT=1 ./nomain/host $init $w 2>&1
        echo "status=$?"
    done
    echo "-- host $init boxes, CEESAFE_FAIL_ALLOC_AT=3:"
    CEESAFE_FAIL_ALLOC_AT=3 ./nomain/host $init boxes 2>&1
done

echo "== freestanding: the environment's ceesafe_panic"
(cd freestanding/fs && "$C" build --emit obj --offline -o ../fs.o)
echo "fs.o undefined: $(nm -u freestanding/fs.o | tr '\n' ' ')"
echo "fs.o global: $(nm -gU freestanding/fs.o | awk '{print $3}' | tr '\n' ' ')"
clang freestanding/host.c freestanding/fs.o -o freestanding/host && ./freestanding/host x; echo "status=$?"
"$C" check --profile freestanding freestanding/vector.cee 2>&1 | head -1
(cd freestanding/fs2 && "$C" build --emit obj --offline -o ../fs2.o)
echo "-- two freestanding objects:"
clang freestanding/two.c freestanding/fs.o freestanding/fs2.o -o freestanding/two 2>&1 | grep -E '^ld:'

echo "== names: an export in the runtime's namespace"
"$C" check names/reserved.cee 2>&1 | grep error

echo "== weak: a weak default overridden by the host, from an object and from an archive"
(cd weak && clang -c rt.c -o rt.o && rm -f librt.a && ar rcs librt.a rt.o && clang host.c rt.o -o d && ./d \
    && clang -DOVERRIDE host.c rt.o -o o && ./o && clang -DOVERRIDE host.c librt.a -o oa && ./oa)

echo "== rust_host: a hand-written extern block (G9)"
(cd rust_host && rustc --edition 2024 -O main.rs -o right -C link-arg=../g8/alpha.o && ./right)
(cd rust_host && rustc --edition 2024 -O --cfg wrong main.rs -o wrong -C link-arg=../g8/alpha.o 2>/dev/null; ./wrong; echo "status=$?")
(cd g8/alpha && "$C" build --emit c --offline -o ../alpha_c)
echo "-- the same wrong declaration in C, with ceesafe_exports.h:"
clang -fsyntax-only -Ig8/alpha_c rust_host/wrong.c 2>&1 | head -1
echo "-- ceesafe_exports.h:"
cat g8/alpha_c/ceesafe_exports.h
echo "-- a Rust extern \"C\" hook that panics:"
(cd rust_host && rustc --edition 2024 hook_unwind.rs -o hook_unwind && ./hook_unwind > hook_unwind.txt 2>&1; echo "status=$?"; grep -v '^ ' hook_unwind.txt | grep -v '^$' | head -3; rm -f hook_unwind.txt)

echo "== msvc: --emit obj --cc cl"
(cd g8/alpha && "$C" build --emit obj --offline --cc cl -o ../alpha_cl.o 2>&1 | head -1)

echo "== cxx_host: a C++ host including ceesafe_exports.h"
echo "__cplusplus guards in the header: $(grep -c '__cplusplus' g8/alpha_c/ceesafe_exports.h)"
clang++ -std=c++17 -Ig8/alpha_c cxx_host/host.cpp g8/alpha.o -o cxx_host/host 2>&1 | grep -E 'Undefined|alpha_sum' | head -3

echo "== exe: the generated C main of a one-line program"
"$C" build --emit c -o exe/out exe/main.cee && sed -n '/^int main/,/^}/p' exe/out/main.c

echo "== threads: two threads entering scratch frames (threads/run.sh)"
bash threads/run.sh 2>&1

echo "== align: a host allocator aligned only for max_align_t (align/run.sh)"
bash align/run.sh 2>&1 | grep -v 'Abort trap'

echo "== elf: the version reference and the package marker under ld.lld (elf/run.sh)"
bash elf/run.sh 2>&1

echo "== lto: --cflag and the runtime; joining the host's LTO (lto/run.sh)"
bash lto/run.sh 2>&1

echo "== rust_sig: a stale generated Rust binding under ld.lld --gc-sections (rust_sig/run.sh)"
bash rust_sig/run.sh 2>&1
