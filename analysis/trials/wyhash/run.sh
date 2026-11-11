#!/bin/sh
# Builds Bun's Rust wyhash and the CeeSafe port (ceebun/bun_wyhash in the trial clone) into one program, checks that
# they agree, and times both. Needs: the trial clone, ceesafec 0.31.0, LLVM 23's clang and llvm-ar on the PATH, and
# Bun's Rust toolchain.
# usage: sh run.sh <trial clone> <ceesafec> <work directory>
set -e
trial=$1; ceesafec=$2; work=$3; here=$(cd "$(dirname "$0")" && pwd)
toolchain=nightly-2026-09-15
flags="--edition 2024 -C opt-level=3 -C target-cpu=apple-m1 -C panic=abort -C codegen-units=1"
mkdir -p "$work/pkg/src"
printf '[package]\nname = "wybench"\nversion = "0.1.0"\nkind = "object"\n\n[dependencies]\nbun_wyhash = { path = "%s/ceebun/bun_wyhash" }\n' "$trial" > "$work/pkg/ceesafe.toml"
echo '// The archive for the benchmark.' > "$work/pkg/src/lib.cee"
(cd "$work/pkg" && "$ceesafec" fetch --offline && "$ceesafec" build --emit lib --offline --cc clang --ar llvm-ar --cflag -O3 --cflag -mcpu=apple-m1 -o "$work/out/libwybench.a")
rustc +$toolchain $flags --crate-type rlib --crate-name bun_wyhash "$trial/src/wyhash/lib.rs" -o "$work/libbun_wyhash.rlib"
rustc +$toolchain $flags --extern bun_wyhash="$work/libbun_wyhash.rlib" -L "$work/out" -l static=wybench "$here/bench.rs" -o "$work/bench"
"$work/bench"
