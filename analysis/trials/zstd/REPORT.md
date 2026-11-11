# Trial: `bun_zstd` swapped for CeeSafe inside Bun's `main`

**Date:** 2026-11-11. **Bun:** `main` at the pin `89452d2ac137`. **Compiler:** ceesafec built from branch `impl/0090`
(0.30.0 plus ADR 0090, to be released as 0.31.0). **Machine:** MacBookPro (arm64).

**Question:** can a crate whose API hands a `Vec<u8>` across the boundary be swapped, with no copy and no loss of speed?
`bun_csrf` (`../csrf/REPORT.md`) lent every buffer for the call. `bun_zstd` appends to the caller's `Vec<u8>`, grows
it, and returns new ones.

**Answer:** yes. Bun's tests pass in release and debug + ASAN builds, and the release timings are the same as stock
Bun's within noise.

**Where the trial is:** the local clone `~/dev/CeeSafeApps/ceebun-trial`, branch `ceebun/main-trial`, commit
`b52dccc65e`. It is not pushed anywhere. The stock build is the worktree `~/dev/CeeSafeApps/ceebun-stock` at the pin.

## 1. Results

**Bun's tests** (`BUN_GARBAGE_COLLECTOR_LEVEL=1 BUN_FEATURE_FLAG_INTERNAL_FOR_TESTING=1`), as pass / skip / fail:

| Test file | Release | Debug + ASAN |
|---|---|---|
| `test/js/bun/util/zstd.test.ts` | 95 / 5 / 0 | 99 / 1 / 0 |
| `test/js/web/fetch/fetch-compress.test.ts` | 32 / 0 / 0 | 32 / 0 / 0 |
| `test/js/web/fetch/fetch-gzip.test.ts` | 89 / 0 / 0 | 89 / 0 / 0 |
| `test/js/bun/archive.test.ts` | 170 / 1 / 0 | 170 / 1 / 0 |
| `test/regression/issue/18413-all-compressions.test.ts` | 6 / 0 / 0 | 6 / 0 / 0 |
| `test/regression/issue/18413-truncation.test.ts` | 12 / 0 / 0 | 12 / 0 / 0 |
| `test/regression/issue/20053.test.ts` | 3 / 0 / 0 | 3 / 0 / 0 |
| `test/js/web/streams/compression.test.ts` | 72 / 1 / 0 | 73 / 0 / 0 |

- ASAN reported nothing in the debug runs.
- The release build skips five tests the debug build runs. They were not compared with a stock build's skips.
- `test/internal/builtins-manifest.test.ts` could not run: it needs WebKit's source (`Source/JavaScriptCore/aot`),
  which is not on this machine.

**Timing, two release builds** (`bench.js`; nanoseconds per call, each the median of 15 rounds, and the table the
median of three alternating runs):

| Case | Path | Stock | Trial |
|---|---|---|---|
| Compress 1 KB | `compress_append` | 4,681 | 4,703 |
| Compress 1 MB | `compress_append` | 1,993,599 | 2,063,248 |
| Decompress 1 KB | `decompress_alloc`, size in the header | 2,951 | 2,941 |
| Decompress 1 MB | `decompress_alloc`, size in the header | 550,177 | 549,801 |
| Decompress 1 MB, size unknown | `decompress_alloc`, streaming | 601,734 | 605,308 |
| Fetch a 1 MB zstd body | `StreamingDecoder` | 869,533 | 884,683 |

The runs of one binary differ from each other by up to 6%, more than the two binaries differ. This is the fair
comparison the `bun_csrf` report lacked: both sides optimised, with CeeSafe's C in Bun's ThinLTO.

**Size:** the trial's `bun` is 16,544 bytes larger than stock (132,333,408 against 132,316,864).

**Allocation report** (debug build, `CEESAFE_ALLOC_REPORT=1`, one compress and one decompress of 200,000 bytes):
`ceesafe alloc: attempts=1 live=0` and `ceesafe alloc: given=2 taken=1`. Buffers crossed in both directions and
CeeSafe held nothing at exit.

## 2. The boundary

- **Slices are lent**, as in `bun_csrf`: pointer and length, for the call.
- **A `Vec<u8>` changes sides** (CeeSafe ADR 0090). The Rust shim takes the caller's `Vec` apart (`mem::take`,
  `ManuallyDrop`); CeeSafe takes the block with `Vector.fromForeign`, works on it as a `Vector<u8>`, and gives it back
  with `Vector.intoForeign`; the shim rebuilds the `Vec` with `Vec::from_raw_parts`. A new vector is given the same
  way. Nothing is copied.
- **Why that is sound here:** both sides allocate from Rust's `#[global_allocator]` (mimalloc, or the C library's
  under ASAN; ADR 0088 stage B). It frees a block by its address and reallocates one whatever layout it was allocated
  with, and `ceebun_realloc` returns a 16-aligned block. This is outside what Rust documents for
  `Vec::from_raw_parts`; the allocator defines it.
- **Spare capacity:** where Rust writes into `spare_capacity_mut()` and calls `commit_spare`, CeeSafe writes through
  `viewMut().ptr` above the length and calls `setLength`.
- **`StreamingDecoder`** is a CeeSafe value in a `Box`. Rust holds its address (`Box.intoRaw`) and returns it in
  `Drop` (`Box.fromRaw`). Rust's decoder was not boxed, so this adds one allocation per decoder.
- **Errors:** `ZstdError` crosses as a `u8` code; `Result::Err`'s name crosses as zstd's static C string.
- **What stays in Rust:** `pub mod c` (other crates call zstd directly) and the `embed_compressed!` macro, which
  expands in the caller's crate.

## 3. Size of the port

| | Lines |
|---|---|
| Rust crate before | 860 |
| Rust shim after | 584 |
| CeeSafe port (`lib.cee`) | 552 |
| CeeSafe exports (`exports.cee`) | 244 |

The shim and the exports are the cost of the boundary: 12 exports, each declared three times (CeeSafe, Rust,
`ceebun_host.c`). `--emit rust` (ADR 0088 stage C) would remove the Rust and C copies.

## 4. Build

- **One umbrella package.** `ceebun/ceebun` (`kind = "object"`) depends on `bun_csrf` and `bun_zstd`, now both
  libraries. The archive carries the exports of both: 14.
- **`scripts/build/ceesafe.ts`** builds the umbrella; nothing else in the build changed.

## 5. Gaps and deviations

1. **A borrowed field was avoided.** Rust's private `ZstdReaderArrayList` holds `&mut Vec<u8>`. The port passes the
   list to `readAll` instead. Whether a CeeSafe struct can hold a mutable borrow was not tried.
2. **`bun-sema` is not covered.** `src/sema/standalone` builds its own binary, depends on `bun_zstd`, and has its own
   `main` without `ceebun_init`. It is not part of `bun run build` and was not built; it is expected not to link.
3. **`Result` is `ZstdResult`.** CeeSafe's own `Result` has the name.
4. **Constants written out.** `usize`'s maximum and zstd's two content-size sentinels are literals.
5. **The compiler requirement** in the manifests is `>=0.30.0` with a comment, because the `impl/0090` compiler still
   reports 0.30.0. It becomes `>=0.31.0` at the release.

## 6. Verdict

ADR 0090 does what it was written for: a crate that hands `Vec<u8>` across the boundary swaps with no copy and no
measurable cost. For the hybrid approach of `ROADMAP.md` §2 this closes the two items the `bun_csrf` trial left open:
a leaf crate that hands ownership to Rust, and release timings against stock Bun.
