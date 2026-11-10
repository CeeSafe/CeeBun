#!/bin/bash
# ADR 0088 probe (§1.10): does a stale Rust binding fail to link under ld.lld --gc-sections? ELF, cross-built for
# aarch64-linux-android (a no_std staticlib needs only core), linked freestanding.
cd "$(dirname "$0")"
LLD=${LLD:-ld.lld}
T="--target=aarch64-linux-android -ffreestanding -fno-pic -O2 -ffunction-sections -fdata-sections"
rm -rf out && mkdir out
clang $T -c lib.c -o out/lib.o && clang $T -c start.c -o out/start.o
for b in used named; do
    rustc --edition 2024 --target aarch64-linux-android --crate-type staticlib -C panic=abort -O $b.rs -o out/lib$b.a
    for gc in "" --gc-sections; do
        if $LLD $gc -e _start out/start.o out/lib.o out/lib$b.a -o out/x 2>out/err; then r="LINKS (stale binding)"
        else r="fails: $(grep -o 'undefined symbol: [a-z_0-9]*' out/err | head -1)"; fi
        echo "rust binding, $b, ${gc:-no gc}: $r"
    done
done
