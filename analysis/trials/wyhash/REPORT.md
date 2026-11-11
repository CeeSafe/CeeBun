# Trial: Bun's wyhash in CeeSafe, timed against Bun's Rust

**Date:** 2026-11-11. **Bun:** `main` at the pin `89452d2ac137`. **Compiler:** ceesafec 0.31.0 for §2; 0.32.0 for §4. **Toolchain:** Bun's
own, rustc `nightly-2026-09-15` and clang, both LLVM 23, `-O3`, `-mcpu=apple-m1`. **Machine:** MacBookPro (arm64).

**Question:** is a CeeSafe port faster than the Rust it replaces? `bun_csrf` and `bun_zstd` could not say: C
libraries do their work. `bun_wyhash` is a hash function written in the language itself, a tight arithmetic loop.

**Answer:** no. It is equal on inputs of 1 KB and more, and a little slower on short keys. Nowhere is it faster.

## 1. What was ported and how it was timed

- **Ported:** the one-shot path of `Wyhash` (`Wyhash::hash`, the function behind `Bun.hash()`), as `ceebun/bun_wyhash`
  in the trial repository. Not ported: the streaming `update`/`final_` and the older `Wyhash11`.
- **Harness** (`bench.rs`, `run.sh`): one program holds Bun's Rust source of the crate, unchanged, and the CeeSafe
  archive. Both are called through the same out-of-line C-ABI function pointer. Each figure is the lowest of three
  medians of 21 rounds, the sides alternating.
- **Agreement:** the two give the same hash on 1,224 inputs: every length from 0 to 300 and five larger ones, with
  four seeds.

## 2. Results

Nanoseconds per call (`results.txt`), with the difference from Rust:

| Input | Rust | CeeSafe, safe code | CeeSafe, short keys unchecked |
|---|---|---|---|
| 8 bytes | 2.82 | 3.15 (+12%) | 2.88 (+2%) |
| 16 bytes | 2.83 | 3.18 (+12%) | 2.98 (+5%) |
| 32 bytes | 3.20 | 3.73 (+16%) | |
| 64 bytes | 4.61 | 4.69 (+2%) | |
| 256 bytes | 10.40 | 10.55 (+1.5%) | |
| 1 KB | 38.97 | 39.20 (+0.6%) | |
| 64 KB | 2,676 | 2,680 (+0.1%) | |
| 1 MB | 43,017 | 43,215 (+0.5%) | |

The third column changes only keys of 4 to 16 bytes; longer inputs take the safe path.

## 3. What the numbers mean

- **Bun's Rust here is not safe Rust.** It reads through raw pointers in `unsafe` blocks, to remove bounds checks.
  The CeeSafe of the middle column has no unsafe code in the hash.
- **Large inputs: equal, with safe code.** The first safe version checked every read and was 35–55% slower from 256
  bytes up. Slicing one 48-byte block per round, so the block is checked once, removed the difference. The
  compiled function has 18 conditional branches where the first version had 32 (Rust's has 14), and each
  multiply is one `mul` and one `umulh`, as in Rust's.
- **Short keys: safe CeeSafe is 12–16% slower**, a third to half a nanosecond. The four reads are at offsets that
  depend on the length, so their checks stay. Written unchecked, as Rust writes them, 8 and 16 bytes come within
  2–5%.
- **Why parity is the ceiling.** Rust compiles through LLVM; CeeSafe compiles to C that clang compiles through the
  same LLVM. For arithmetic and memory code the two meet at the same machine code.

## 4. Gaps found

1. **No 128-bit multiply. Closed in ceesafec 0.32.0** (CeeSafe ADR 0092, `x.mulHigh(y)`). wyhash needs the high half
   of a 64 × 64 product. With 0.31.0 the port built it from 32-bit halves, which LLVM 23 folds into one `umulh` and
   Apple clang 21 does not. The port now calls `a.mulHigh(b)`, which is one instruction with either compiler.
   Nanoseconds per call, the CeeSafe side built with Apple clang 21:

   | Input | Rust | CeeSafe 0.31.0, hand-written | CeeSafe 0.32.0, `mulHigh` |
   |---|---|---|---|
   | 16 bytes | 2.72 | 7.44 (2.5 times) | 3.05 (+12%) |
   | 1 KB | 37.64 | 149.21 (3.8 times) | 37.53 (equal) |
   | 1 MB | 41,556 | 143,618 (3.3 times) | 41,689 (equal) |

   The middle column is an earlier run, and its multiples are against that run's Rust figures (3.02, 39.51 and
   43,153 ns). `results.txt` is a run of the 0.32.0 port with LLVM 23: the same ratios to Rust as §2.
2. **No unaligned load from a raw pointer.** `p.read()` needs an aligned pointer. The unchecked reads go through
   `Slice.fromRaw(p, 4).readLE<u32>(0)`, which compiles to one load. CeeSafe ADR 0093 (`p.readUnaligned()`) is
   accepted and not implemented; it would make this read as what it does, not faster.

## 5. Not done

- **Not swapped inside Bun.** There the Rust hash is force-inlined into every hash-map lookup; a fair test needs two
  more release builds. The package is not wired into the trial's build.

## 6. Verdict

On a hot arithmetic loop, safe CeeSafe matches hand-tuned unsafe Rust on large inputs, and comes within a few percent
on short keys when written the same unchecked way. That supports "CeeSafe can match Rust". It does not support
"CeeSafe is faster than Rust", and the performance work stops here.
