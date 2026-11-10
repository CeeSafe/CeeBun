# Trial: `bun_csrf` swapped for CeeSafe inside Bun 1.4.4

**Date:** 2026-11-10. **Compiler:** ceesafec 0.27.0. **Machine:** MacBookPro (arm64), debug + ASAN builds.

**Question:** can one Rust crate inside Bun be replaced by CeeSafe code, with Rust and CeeSafe linked into one binary,
and Bun's own tests still passing? The answer decides whether CeeBun becomes a fork of Bun that swaps crates one at a
time (see `ROADMAP.md` §2).

**Answer:** yes for this crate, end to end. Past one crate, not until two compiler bugs are fixed (G8, G1). And
crate-by-crate swapping stops at the foundation crates.

**Where the trial is:** a local clone at `~/dev/CeeSafeApps/ceebun-trial`, branch `ceebun/csrf-trial`, with two
commits: `a8ffc47ede` (the CeeSafe packages) and `28bb360c8f` (the Rust shim and the build change). It is not pushed
anywhere.

## 1. Results

| Test file | Stock | Trial |
|---|---|---|
| `test/js/bun/util/csrf.test.ts` | 40 pass, 0 fail, 162 expects | 40 pass, 0 fail, 162 expects |
| `bun-cryptohasher.test.ts` | 109 pass | 109 pass |
| `base64-url-safe-encode.test.ts` | 6 pass | 6 pass |
| `crypto-hmac-algorithm.test.ts` | 5 pass | 5 pass |
| `text-encoder.test.js` | 46 pass | 46 pass |
| `hash.test.js` | 28 pass | 28 pass |

No test was skipped, deleted or changed.

**Cross-check:** each binary generated 54 tokens (6 algorithms × 3 encodings × 3 session ids) and verified both
binaries' tokens: with the right options, a wrong session, a wrong secret, and 10 mangled variants under each of the 3
decoders, 1,782 verdicts per set. Stock and trial gave identical verdicts on both sets.

**Timing (ns per call):**

| Case | Stock | Trial |
|---|---|---|
| No session, base64url: generate | ~10,000 | ~9,300 |
| No session, base64url: verify | ~10,800 | ~7,300 |
| Session id, hex: generate | ~16,000 | ~13,900 |
| Session id, hex: verify | ~20,500 | ~10,800 |

This is not a fair comparison: the debug build compiles Rust unoptimised, while ceesafec compiles its C at `-O2`. It
shows only that the boundary adds no measurable cost. A fair comparison needs two release builds.

## 2. The boundary

The call path: `src/runtime/api/csrf_jsc.rs` (unchanged) → the Rust shim (`src/csrf/lib.rs`, same public API) → two
CeeSafe exports.

| Export | Arguments | Result |
|---|---|---|
| `bun_csrf__generate` | secret ptr/len, session ptr/len, `u64` expiry, `u8` algorithm, the caller's 512-byte buffer | `size_t` length; 0 is `TokenCreationFailed` |
| `bun_csrf__verify` | token, secret, session (each ptr/len), `u64` max age, `u8` encoding, `u8` algorithm | `bool` |

- **Types:** slices cross as pointer and length. `TokenFormat` is `#[repr(u8)]` in Rust and `@repr(u8)` in CeeSafe.
  `Algorithm` crosses as its Rust discriminant `as u8`, pinned by a Rust `const` assertion and mapped by a 19-arm match
  (it could not be a CeeSafe `@repr` enum, because of G1).
- **Ownership:** no memory crosses allocators. Rust lends every buffer for the call; CeeSafe's one allocation (a
  `Vector` for `payload || session_id`) is freed by CeeSafe. CeeSafe allocates with `malloc` (ASAN's here, the system's
  on macOS release, mimalloc on Linux where it overrides `malloc`); Rust uses mimalloc.
- **`unsafe`:** CeeSafe has 26 `unsafe` expressions in 22 functions, each with a `/// Safety:` line, and no `unsafe fn`.
  19 are one-function BoringSSL wrappers (`RAND_bytes`, `CRYPTO_memcmp`, `HMAC`, 16 `EVP_*` getters), 1 wraps simdutf,
  and 6 are in the two exports (5 `Slice.fromRaw`, 1 `Ptr.toBorrowMut`), where C pointers become slices. The ported
  logic has none. The Rust shim has 2 `unsafe` blocks.
- **Code:** 744 lines of CeeSafe in `ceebun/`: `bun_csrf` 499 (the port, the part of `bun_base64` it uses, the
  exports), `bun_boringssl_sys` 107, `bun_sha_hmac` 67, `bun_core` 71 (`trim`, hex decoding, `milliTimestamp`).

## 3. The CeeSafe runtime without a CeeSafe `main`

The generated `main` only reads `CEESAFE_FAIL_ALLOC_AT` and `CEESAFE_ALLOC_REPORT`, keeps argv, and prints the
allocation report at exit. Tested with a C `main` calling exports, and inside Bun:

| Feature | Without a CeeSafe `main` |
|---|---|
| Allocation (`Vector`, `Box`) | works |
| Threads (`Thread.spawn`, `Arc`/`Mutex`) | work |
| `Async.run` | works |
| `Process.argument` | always empty |
| `CEESAFE_ALLOC_REPORT`, `CEESAFE_FAIL_ALLOC_AT` | silently ignored: no allocation-failure sweeps inside Bun |
| Panic | prints `ceesafe panic: … at file:line:col`, then `abort()`; in this ASAN build Bun's crash handler reports nothing, because Bun skips its signal handlers under ASAN (`reset_on_posix`), so a release build would report an abort with a stack, but not CeeSafe's message, file or line |

## 4. Build integration

- **New `scripts/build/ceesafe.ts` (77 lines):** a ninja rule `ceesafe_obj` running
  `$CEESAFEC build --emit obj --offline --cc <Bun's clang> [--cflag -mmacosx-version-min=…] [--cflag -g]`, with every
  `.cee` file and manifest under `ceebun/` as implicit inputs.
- **Small edits:** `ninja.ts` +2, `rules.ts` +4, `bun.ts` +3/−1 (the object joins the link after the Rust rlibs).
  `src/csrf/Cargo.toml` drops `bun_base64` and `bun_boringssl_sys`. Bun's duplicate-symbol check passes.
- **Tools installed on the Mac:** Bun 1.4.4 needs LLVM clang 23.1, so `brew install llvm@23` (keg-only, as Bun's
  `CONTRIBUTING.md` says), plus `automake`, `coreutils`, `gnu-sed`, `libtool`, `libiconv`.

| Build | Time |
|---|---|
| Stock debug build from scratch | 371 s |
| First trial rebuild | 57 s |
| Rebuild after a `.cee`-only change | 21–35 s, almost all relinking |
| `ceesafec build --emit obj` alone | ~0.5 s (57 KB object) |

## 5. Gaps, most important first

1. **G8: two CeeSafe objects cannot be linked together.** Each `--emit obj` object carries the whole runtime, about
   120 global `ceesafe_*` symbols. Repro: two packages, each `build --emit obj`, linked into one C program →
   `duplicate symbol '_ceesafe_scratch_enter_child'` (reproduced independently). Workaround: one umbrella package that
   depends on every swapped crate. Needed: `--emit obj` without the runtime, and a runtime object linked once.
2. **G1: a `@repr` type declared in a dependency makes invalid C**, in every build, executables included, while
   `ceesafec check` passes. Repro: `dep` declares `@repr(C) struct Pair`, `root` uses it → `ceesafe_exports.h` has
   `struct dep.Pair` and fails to compile (reproduced independently). Workaround: every `@repr` type in the root
   package. Needed: C names qualified by package in the header and the generated C.
3. **D1: CeeSafe cannot call a Rust crate's API.** A limit of the approach, not a bug. Each swapped crate re-ports what
   it uses from its Rust dependencies (here ~245 lines from 4 crates), and those copies can drift. With `cargo metadata`
   (123 workspace crates): `bun_core` has 100 dependents, `bun_alloc` 55, `bun_collections` 42; only 10 crates have no
   workspace dependencies.
4. **G6: no allocator hook** (closed in §7). `ceesafe_platform_alloc` is a strong symbol calling `malloc`. A crate that hands
   ownership to Rust (a returned `Vec`) needs CeeSafe to allocate from mimalloc or `bun_alloc`.
5. **G2: no panic hook.** A panic reaches Bun only as `SIGABRT`: without CeeSafe's message, file and line (correction, 2026-11-10: the silence seen in the trial came from the ASAN build, see §3). Needed: a weak `ceesafe_panic` or a registration call, routed to Bun's `Bun__crashHandler`,
   and an exported runtime initialiser for embedding.
6. **G9: no Rust binding generator.** The shim's `extern` block and enum mapping are hand-written; nothing checks them
   against the exports, so a wrong parameter order links and runs.
7. **G3: a slice local cannot be re-pointed:** `var t = s; t = t[0..n];` → N0246. Common in parsers.
8. **G4: an array length cannot name another package's constant:** `[u8; dep.SIZE]` → N0200.
9. **G5: no compile-time loops:** a 256-entry table cannot be computed (`static T = table();` → N0338).
10. **G7: a constant cannot have an enum type:** `const D: Algorithm = Algorithm.Sha256;` → N0217.
11. **G10: no modules inside a package:** merging `bun_base64` into `bun_csrf` forced renames.
12. **Minor:** `64usize as u32` rejected even for a constant that fits; `?? { return … }` does not parse on a
    `Result`; no `Enum.fromIndex`.

## 6. ADR 0088 stage A in the trial (ceesafec 0.28.0)

**Date:** 2026-11-10. The §5 "CeeBun" test of CeeSafe ADR 0088, on the same clone and branch, commit `4176b669d2`.

**The change:**
- `scripts/build/ceesafe.ts`: one `ceesafec build --emit lib` archive in place of `--emit obj`, with Bun's flags for
  C that is not its own (`computeDepFlags`: target, sysroot, `-mcpu`, frame pointers, ASAN, `-flto=thin`). A new
  ceesafec or clang rebuilds it. Configure refuses Windows targets (stage E).
- `ceebun/host/ceebun_host.c` (new): `ceebun_init` calls `ceesafe_init` with Bun's argv and a panic hook that formats
  the panic and calls `Bun__crashHandler`. Debug builds also read `CEESAFE_ALLOC_REPORT` and `CEESAFE_FAIL_ALLOC_AT`
  and print the report at exit; a release `bun` reads neither, since every child process would inherit them. The
  file re-declares the exports as the Rust shim does, so a CeeSafe signature change is a C compile error. A change to
  the shim alone, a reordering of same-typed parameters, and enum values are not checked (stage C's `--emit rust`).
- `src/runtime/bin_entry/mod.rs`: calls `ceebun_init` right after `bun_crash_handler::init()`.
- Manifests: `ceesafec = ">=0.28.0"`.

**Results:**

| Check | Debug + ASAN | Release (ThinLTO) |
|---|---|---|
| The six test files of §1 | all pass, same counts | all pass, same counts (`hash.test.js` needs the test harness's `BUN_GARBAGE_COLLECTOR_LEVEL` and `BUN_FEATURE_FLAG_INTERNAL_FOR_TESTING`, as for any release build) |
| Bun's duplicate-symbol check | 0 | 0 |
| Archive members | ASAN-instrumented | LLVM bitcode, in Bun's ThinLTO link |
| `panic("…")` (temporary patch, reverted) | `panic(main thread): CeeSafe: explicit panic: ceebun trial: deliberate panic at src/exports.cee:83:9`, a stack through the hook, the export, the Rust shim and JSC, status 134 | the same line in Bun's full crash report ("oh no: Bun has crashed", bun.report link), status 134 |
| Index out of bounds (same patch) | `CeeSafe: index out of bounds at src/exports.cee:86:34`, status 134 | the same, in the full crash report |
| `CEESAFE_ALLOC_REPORT=1` | `ceesafe alloc: attempts=2 live=0` at exit | ignored |
| `CEESAFE_FAIL_ALLOC_AT=1` / `2` | `generate` throws "Failed to create CSRF token" / `verify` returns false | ignored |

**What it closes:** G2 (the panic now reaches Bun's crash handler with CeeSafe's message, file and line, in both
builds, where §3's ASAN build reported nothing), the missing initialiser (§3: failure sweeps and the allocation
report now work inside a debug Bun), and LTO (CeeSafe was a native object outside Bun's ThinLTO).

**Still open:**
- **G9 for Rust** (stage C): the shim is matched to the C copy by hand.
- **G6** (stage B): CeeSafe still allocates with the C library's `malloc`. Closed in §7.
- **G8 for two separately built archives** (stage D): CeeBun keeps one umbrella package.
- **Crash reports of a fork.** A CeeSafe panic now produces Bun's "This indicates a bug in Bun" message and a
  bun.report link for upstream Bun's team. A public CeeBun build needs its own report target.
- **Not measured:** release timings against a stock release build (§1's timings are debug only).
- **Reviews:** two adversarial reviews (runtime soundness, build integration). Their findings are fixed in the change
  above, except three kept as they are: the headers are rewritten on each archive build (one small C file
  recompiles), a `.cee` file added later is seen only after the next configure, and the link order would matter only
  to GNU ld, which Bun does not use.

## 7. ADR 0088 stage B in the trial (ceesafec 0.29.0)

**Date:** 2026-11-11. The trial clone's commit `f16561b48e`.

**The change:**
- `ceebun/host/ceebun_host.c`: `ceebun_init` gives `ceesafe_init` the allocator that `bin_entry`'s
  `#[global_allocator]` uses. In a build without ASAN that is mimalloc, through `mi_malloc_aligned`,
  `mi_zalloc_aligned` and `mi_realloc_aligned` at 16 bytes, and `mi_free`. The aligned forms are needed because plain
  `mi_malloc` gives a small block only its size's alignment (8 for an 8-byte block), and CeeSafe panics on a block
  aligned below 16. `mi_free` frees blocks from either side. Under ASAN no allocator is given: Rust uses the system
  allocator there, and ASAN sees every block from both sides.
- `scripts/build/ceesafe.ts`: the host file is compiled against mimalloc's headers, after mimalloc is built, with
  `CEEBUN_MIMALLOC` set exactly when `cfg.asan` is not (Rust's `bun_asan`). `bun.ts` passes it the mimalloc dependency.
- Manifests: `ceesafec = ">=0.29.0"`.

**Results:**

| Check | Debug + ASAN | Release (ThinLTO) |
|---|---|---|
| The six test files of §1 | all pass, same counts | all pass, same counts |
| Bun's duplicate-symbol check | 0 | 0 |
| The allocator CeeSafe uses | the C library's `malloc` | mimalloc |

**The hook in the release binary:** 100 `generate`/`verify` pairs with a session id, under lldb with breakpoints on
the hook's functions: `alloc` 201 calls, `free` 200, `alloc_zeroed` and `realloc` none. Each `sign` with a session id
allocates one `Vector` and frees it; the 201st block is `argv`'s copy, kept until exit. After ThinLTO, `ceebun_alloc`
ends in mimalloc's aligned allocation path and `ceebun_free` is a tail call to `mi_free`.

**What it closes:** G6. CeeSafe and Rust allocate from one heap in both builds, so a block can be allocated on one
side and freed on the other.

**Still open:**
- **No block crosses the boundary yet.** `bun_csrf` frees everything it allocates. A second leaf crate that returns an
  owned buffer to Rust would test it (`ROADMAP.md` §2).
- **Windows:** Bun calls `mi_*` directly there too, so the same host code would apply, but CeeBun does not build for
  Windows (ADR 0088 stage E).
- G9 for Rust (stage C), G8 for two separately built archives (stage D), and the crash-report target and release
  timings of §6.

## 8. Verdict

- **Leaf crates with C-shaped APIs: workable and cheap.** The build change is small, Bun's tests run unchanged.
  `bun_csrf` is near the ideal case: two functions, slices in, a length or a bool out, one dependent.
- **More than one crate: not until G8 and G1 are fixed.**
- **It stops at APIs that carry Rust types** (`bun_core::String`, `Vec`/`Box` ownership, generics, traits, callbacks):
  each needs a hand-designed C facade and a shared allocator (G6), or its callers swapped at the same time.
- **It stops at the foundation crates.** `bun_core`, `bun_alloc` and `bun_collections` cannot be swapped while Rust
  above them still uses them; swapping top-down means re-porting their pieces into every swapped crate (D1).
- **Recommendation:** use crate swapping in a fork as a proving and benchmarking harness for leaves and edges, and keep
  the whole-program port for the core. Fix G8 and G1 first (an ADR each), then G6 and G2.
