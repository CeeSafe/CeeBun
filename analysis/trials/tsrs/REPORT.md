# Trial: two crates of tsrs (TypeScript's checker in Rust) in CeeSafe

**Date:** 2026-11-11. **tsrs:** [oxc-project/tsrs](https://github.com/oxc-project/tsrs) `main` at `13a31a4cac36`
(Apache-2.0; 24 MB of Rust in 38 crates). **Compiler:** ceesafec 0.32.0. **Toolchain:** rustc 1.99.1 (tsrs's own),
Apple clang 21. **Machine:** MacBookPro (arm64). **Code:** `~/dev/CeeSafeApps/tsrs-trial`, branch `ceesafe/trial`
(local, not published).

**Question:** does the proof made on Bun hold on a second Rust code base, and on code that is data structures and
algorithms in the language itself, where Bun's two crates were wrappers around C libraries?

**Answer:** yes for correctness, with one Rust wrapper kept for a missing CeeSafe feature. For speed: equal where the
work is inside CeeSafe, 13–40% slower per call where a small function is called across the boundary, and about
twice as slow to build a map.

## 1. What was ported

| Rust | CeeSafe (`ceesafe/` in the trial) | Lines of CeeSafe |
|---|---|---|
| `tsrs_spanmap`: the span map (segment lookups both ways, validation, the interval index) | `tsrs_spanmap` | 800 + 256 of exports |
| `tsrs_core::goslices::sort_func`: Go's pdqsort, which the span map sorts with | `tsrs_core` | 352 |
| `tsrs_sourcemap`'s generator: the mappings encoder (last and pending mapping, base64 VLQ, data-URL base64) | `tsrs_sourcemap` | 379 + 122 of exports |

- **The Rust files keep their public API** and call the CeeSafe exports, so no other crate changed.
- **Stays in Rust:** the types, `TextRange` conversion, JSON (it is `tsrs_core::json`'s), and the generator's sources
  and names (strings, hash maps, `tspath`).
- **Build:** a new crate, `tsrs_ceesafe`, runs `ceesafec build --emit lib` from its build script and links the
  archive. tsrs has several binaries and no one entry point, so the runtime starts on first use, behind a `Once`.
- **Memory:** nothing changes sides. A map, an index and an encoder are CeeSafe boxes that Rust holds by address.
  Lists come back in a buffer Rust lends. tsrs's binaries use different allocators, so the buffer adoption used for
  Bun's `bun_zstd` (CeeSafe ADR 0090) does not apply.

## 2. Correctness

| Check | Result |
|---|---|
| `tsrs_spanmap`'s own tests | 31 pass |
| `tsrs_sourcemap`'s own tests | 40 pass |
| Span map against the original Rust file, generated maps (also unsorted and invalid ones, up to 5,000 segments) | 909,360 questions, the same answers |
| Generator against the original Rust file, generated calls (also rejected ones, and clones) | 87,607 calls, the same results and source maps |
| `tsrs_contentmapper` and `tsrs_api_codec` tests | 16 and 35 pass |
| Content-mapper tests of `tsrs_ast` and `tsrs_compiler` (filtered runs) | 4 and 12 pass |
| The `tsrs` binary on a small file with `--sourceMap` | reports the type error and writes the map |
| Clippy with tsrs's rules, the three changed crates | clean |

The differential tests are in the trial (`crates/*/tests/differential`): each holds the Rust file as it was at the
pin and asks both sides the same questions.

## 3. Speed

Release build, the lowest of 30 or 40 rounds, three runs that agree (`results.txt`). The Rust side is the original
file compiled into the test with tsrs's release profile (fat LTO), so its calls are inlined. The CeeSafe side is
called through the shim and is not inlined: the archive does not take part in rustc's LTO.

| Work | Rust | CeeSafe | Difference |
|---|---|---|---|
| Build the index of 2,000 segments (sort by three keys, build the tree) | 66 µs | 66 µs | equal |
| Validate a 2,000-segment map | 5.7 µs | 4.6 µs | 17–21% faster |
| `virtual_to_original_position` | 40 ns | 46 ns | 15% slower |
| `virtual_to_original_span` | 72 ns | 89 ns | 22–26% slower |
| `original_to_virtual_positions` | 118 ns | 133 ns | 13% slower |
| `original_to_virtual_spans` | 213 ns | 290 ns | 35–37% slower |
| Build a map of 2,000 unordered segments | 27 µs | 50–59 µs | about twice as slow |
| Build a map of 2,000 ordered segments | 5.1 µs | 10.7 µs | about twice as slow |
| Add a mapping to a source map | 17.5 ns | 24.5 ns | 37–41% slower |
| `string()` of a 1.2 MB source map | 0.23–0.25 ms | 0.26–0.29 ms | 12–16% slower |
| `base64_data_url()` of the same map | 1.35 ms | 0.97 ms | 25–31% faster |

What the numbers mean:

- **Work done inside CeeSafe is equal:** the index build is the sort and a loop, with one call across the boundary.
- **Small calls pay for the boundary:** each lookup and each added mapping is one call that is not inlined, 6 to 17
  ns more. The list-returning lookups also allocate on both sides, since no block changes sides. The largest
  difference, `original_to_virtual_spans`, is not explained further.
- **Building a map is twice as slow, and the cause is not established.** The segments are copied twice more than in
  Rust (into the `u32` buffer and out of it), which the ordered row shows costs about 5 µs. The rest of the
  unordered difference is in the sort by one key, although the sort by three keys is equal.
- **The two faster rows are not a language result.** Rust's base64 pushes `char`s through an iterator into a
  `String`; the port writes bytes into a slice. Why validation is faster was not investigated.

## 4. Gaps found in CeeSafe

1. **No once cell.** Rust builds the span map's index on first use in a `OnceLock`. CeeSafe has `Mutex` and atomics
   but nothing that initialises once and then reads without a lock, so the `OnceLock` stays in the Rust shim and the
   index is a second CeeSafe object. A candidate for an ADR.
2. **A qualified interface name in `impl` is rejected with a misleading message.** `impl tsrs_core.Order<T> for X`
   gives N0315 ("is the name of a dependency and cannot also name an item"). It works after
   `import tsrs_core.Order;`. A compiler bug or a diagnostic to fix.

Friction that is by design, not a gap:

- **Shifts and bitwise operators take unsigned operands.** The VLQ encoder's `i64` became a `u64` after its sign
  step.
- **No tuples and no closures compiled per use.** Rust's pairs became small structs. The sort's comparison is an
  interface with a static method, so each sort is compiled for its comparison as Rust's is; a function value would
  be an indirect call.
- **A method that implements another package's interface must be `public`** for that package to call it.
- **Arithmetic is checked.** An overflow panics, as in Rust's debug builds; tsrs's release builds wrap. A CeeSafe
  panic also ends the process, where a Rust panic unwinds.

## 5. Not done

- **tsrs's conformance suite** and eight `tsrs_ls` tests need the `ts-ref` TypeScript checkout, which the trial clone
  does not have. The eight fail looking for it; they were not run on the stock build.
- **Windows and WebAssembly:** the build script handles a native Unix build only. tsrs ships a `wasm32-wasip1` build.
- **Cross-language LTO,** which would remove the per-call cost in §3. It needs a clang of rustc's LLVM version.
- **End-to-end timing of `tsrs`.** The span map is used only with content mappers, and source maps only with
  `--sourceMap`; neither is on the type checker's hot path.

## 6. Verdict

The method carries over: two more crates of a second large Rust project run as CeeSafe behind an unchanged API, with
the same answers as the Rust on about a million generated cases. On speed the result matches the Bun trial's: CeeSafe
equals Rust where the work is, and a hybrid build pays at the boundary. It is not faster than Rust.
