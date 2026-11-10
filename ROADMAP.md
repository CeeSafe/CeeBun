# Porting Bun to CeeSafe: roadmap

**Goal:** show that CeeSafe can replace Rust, by porting Bun (Rust) to CeeSafe, at a pinned commit of Bun's `main`
(§1). The port must pass Bun's own test suite and match its performance.

**Status:** M0 in progress (started 2026-11-09). Nothing is ported yet. The compiler scale test runs, and its first findings are in
`analysis/scale/README.md`.

## 1. Starting point

### Bun at the pinned commit

- **The pin:** Bun's `main` at commit `89452d2ac137` (2026-11-10, "AOT: bun compile, build output, module mocks, fixes
  and new names (#48436)"), 97 commits after the 1.4.4 release (tag `bun-v1.4.4`, commit `38afee6c84fc`,
  2026-10-22). Its `package.json` still says 1.4.4. Decided 2026-11-11: the port follows `main` rather than the
  release, and the pin moves only on purpose (§2).
- **Rust:** about 1.79 million lines, not counting blanks or comments, in 4,157 files and 135 crates (1.4.4: 1.39
  million, 3,221 files, 122 crates). Only about 22,000 lines are generated. Most of the growth is a new ahead-of-time
  compiler (`src/aot`) and the type checker (`src/sema`).

| Part of Bun | Rust lines | Share | At 1.4.4 |
|---|---|---|---|
| Developer tools: linter (`src/lint`), type checker (`src/sema`), formatter (`src/format`), React compiler | 744,014 | 41.5% | 621,113 |
| Runtime: Node and Web APIs, JavaScriptCore glue, servers, SQL, shell, test runner, CLI | 423,197 | 23.6% | 375,959 |
| AOT compiler (`src/aot`, new since 1.4.4) | 210,316 | 11.7% | 0 |
| Transpiler and bundler: parser, printer, AST, bundler, resolver, CSS, source maps, YAML/TOML/Markdown | 227,792 | 12.7% | 204,834 |
| Package manager: `bun install`, semver, patch | 94,126 | 5.2% | 94,374 |
| Core and platform: allocators, collections, I/O, event loop, threads, system calls, uWS glue, `-sys` crates | 94,142 | 5.2% | 92,132 |

Both columns group `src/<crate>` directories the same way (the grouping changed from this table's first version, so
the 1.4.4 column differs slightly from the figures first given for it).

- **Not ported:** about 230,000 lines of C++ (mostly the JavaScriptCore bindings in `src/jsc`) and about 190,000 lines
  of C. Neither is ported: CeeSafe calls the same `extern "C"` functions Rust calls today.
- **Native libraries:** JavaScriptCore, BoringSSL, usockets/uWS, lsquic, SQLite, zlib, zstd, brotli, mimalloc,
  libuv and c-ares are linked unchanged. Two are Rust: **lol-html** (`HTMLRewriter`) and **rust-argon2**. They stay
  linked through their C interfaces until they are ported.
- **Third-party crates:** 25 are runtime dependencies, and 11 of them exist only for macros (`syn`, `quote`, `paste`,
  `strum`, `thiserror`, `bitflags`, …). The others are small: `encoding_rs`, `hashbrown`, `smallvec`, `bcrypt`,
  `blake2`, `sha3`, `rustix`, `libc`, `bstr`, `itoa`, …
- **The tests:** about 60,000 tests and 1.4 million assertions (counted at 1.4.4), written in TypeScript. They don't
  depend on the language Bun is written in, so they are the oracle for the port.

### How Bun's Rust is written

Measured over the hand-written Rust:

| Feature | Count | Per 1,000 lines | At 1.4.4 |
|---|---|---|---|
| `unsafe` blocks, functions and impls | 11,569 | 6.5 | 12,835 |
| Raw pointer types | 12,080 | 6.8 | 12,964 |
| `extern "C"` items | 1,816 | 1.0 | 1,642 |
| Generic functions and types | 18,055 | 10.2 | 15,088 |
| Trait impls / trait definitions | 5,179 / 547 | 2.9 / 0.3 | 5,082 / 540 |
| `dyn` uses / `Box<dyn Fn>` and `impl Fn` | 1,219 / 1,721 | | 717 / 1,009 |
| Macro invocations (distinct macros) | 55,407 (683) | 31.2 | 36,282 (657) |
| `macro_rules!` definitions | 732 | | 697 |
| Const generic parameters / `const fn` | 1,473 / 845 | | 1,409 / 762 |
| `Cell` / `RefCell` | 951 / 180 | | 791 / 128 |
| Thread and atomic sites | 1,875 | | 1,516 |
| async/await | 2 | none in practice | 2 |
| SIMD / inline asm | 28 / 25 | | 18 / 15 |

The macro, const generic and cell rows come from the scripts in `analysis/adr-evidence/` (ADRs 0087, 0083, 0084); the
others from `analysis/bun_rust_features.py`, over 1.77 million hand-written lines (1.37 million at 1.4.4). Both columns
were measured again on 2026-11-11 with the same scripts. `unsafe` and raw pointers went down while the code grew by
29%. Much of the rise in macro invocations is `assert_eq!` and `assert!` (12,113 more).

The code is a faithful port from Zig, with the same architecture and data structures, and it was made with AI agents.
That shows in the heavy use of `unsafe` and raw pointers.

### CeeSafe 0.21.0 against what Bun uses

Each line below was tested with a small program on the installed compiler (`ceesafec run --interp`), unless marked
otherwise. The probes in `analysis/probes` give the same results on 0.24.2 (rerun 2026-11-09).

| Rust feature | CeeSafe 0.21 |
|---|---|
| `dyn Trait`, `Box<dyn Trait>` | ✅ `dyn Interface` |
| Stored callbacks (`Box<dyn FnMut>` in a struct) | ✅ `Box<dyn mut fn(…)>`, owning `move` closures. A closure in a field is called through a local. |
| `impl<T: Bound> Trait for Wrap<T>` | ✅ generic impls |
| Threads, `Arc<Mutex<T>>`, atomics | ✅ also in a native build |
| `extern "C"`, raw pointers, `unsafe` | ✅ a `/// Safety:` line is required |
| Formatting (`format!`, `write!`) | ✅ through `String.append…`; there are no format strings |
| Const generics (`<const TS: bool>`) | ❌ `const` is reserved |
| Pattern guards (`Some(n) if n > 3`) | ❌ |
| `Cell` / `RefCell` | ❌ |
| Default methods in interfaces | ❌ |
| Associated types, iterator trait, slice patterns | ❌ (per the guide; not probed) |
| Macros | ❌ (`macro` is a reserved word) |

- **Allocation:** every allocation returns a `Result` in CeeSafe. Bun's Rust allocates infallibly, so allocations get
  `!` or `?`.
- **Overflow checks:** integer overflow is checked in every CeeSafe build. Rust release builds don't check it.

### The benchmark: Bun's own rewrite from Zig to Rust (May 2026)

Source: <https://bun.com/blog/bun-in-rust>

- **Scope:** 535,496 lines of Zig became about 1,009,000 lines of Rust (PR #30412). One engineer did it in **11 days**,
  with about 50 Claude Code dynamic workflows, up to 64 Claudes at a time (4 worktrees × 16).
- **Cost:** about **$165,000** in API usage, with a pre-release Claude Fable 5.
- **Result:** 100% of the test suite passed on 6 platforms before the merge. 19 regressions turned up later, and all
  were fixed. Release 1.4.0 came about 3 months after the merge.
- **The method, which this roadmap reuses:**
  - A porting guide (`PORTING.md`) and an ownership map (`LIFETIMES.tsv`), each checked by adversarial reviewers.
  - A trial on 3 files first.
  - A mechanical port, file by file: 1 implementer and 2 adversarial reviewers per change, then 1 fixer.
  - Compiler errors used as a work queue, crate by crate.
  - Then the subcommands, then the test suite, locally and in CI.
  - When something goes wrong, fix the process that writes the code, not the code by hand.

### Our own baseline: the mail server port

- **Size:** 33,584 lines of C# became 57,868 lines of CeeSafe, 1.7 times larger.
- **Time:** about 2.5 days (2026-11-04 to 2026-11-06), with compiler fixes made in parallel (ADRs 0074 and 0075).
- **Scale so far:** the largest CeeSafe program is the compiler, at about 85,000 lines. The Bun port would be about
  2.2 million, **25 times larger**.

## 2. Approach

1. **A faithful, mechanical port of Rust to CeeSafe.** Same architecture, same data structures, same files. Idiomatic
   cleanup comes after the port works, as Bun did after its Zig port.
2. **Hybrid: leaf crates swapped inside Bun, the core ported all at once.** Decided 2026-11-11, after the `bun_csrf`
   trial (`analysis/trials/csrf/REPORT.md`, §9):
   - **Leaves and edges, swapped one crate at a time** in a clone of Bun branched from the pinned commit (§1). These
     are crates with C-shaped APIs: slices in, plain values out, few dependents. Each swapped crate is a CeeSafe
     package in one `--emit lib` archive linked into Bun's ThinLTO build, behind a thin Rust shim. Bun's own tests
     check it right away, and a release build is benchmarked against stock Bun. This is the proving and benchmarking
     harness.
   - **The core, ported all at once**, as Bun's blog recommends. The core is `bun_core` (100 dependents), `bun_alloc`
     (55), `bun_collections` (42) and every crate whose API carries Rust types (`bun_core::String`, `Vec`/`Box`
     ownership, generics, traits, callbacks). These crates call each other through Rust types. Swapping them from the
     top down would mean copying their pieces into every swapped crate (gap D1), and those copies would drift.
   - **The swapped crates' code goes into the full port.** The shims and C facades are temporary and are dropped when
     the core lands.
   - **Rules for the clone:**
     - Never merge Bun's `main` into it between pins.
     - Moving the pin takes `git diff <old pin>..<new pin>`: changes to a swapped crate are ported into CeeSafe by
       hand; other crates merge as usual. The clone keeps a list of its swapped crates.
     - Rust and CeeSafe share one heap through the CeeSafe allocator hook (ceesafec 0.29.0). Their blocks are still
       not interchangeable (CeeSafe ADR 0088 §2.5): each side frees what it allocated through its own code, so a
       block CeeSafe hands out comes back through an export. A CeeSafe buffer adopted by Rust without a copy needs a
       later CeeSafe ADR.
     - The clone is local (`~/dev/CeeSafeApps/ceebun-trial`). Publishing it as a fork needs the owner's approval and
       its own crash-report target, because Bun's crash reports go to Oven's bun.report.
3. **Proof first.** Port a self-contained slice that can be benchmarked (milestone M2) before committing to the whole.
4. **Bun's test suite is the definition of done.** No test is skipped or deleted.
5. **Language gaps are fixed in CeeSafe, not worked around in thousands of places.** Each gap gets an ADR in
   `~/dev/CeeSafe/spec/decisions`, as in the mail server port.

## 3. Milestones

### M0: Readiness (4–6 weeks)

Make CeeSafe able to take the port. These are the gaps the measurements above found:

| Work | Why |
|---|---|
| **Compiler scale test:** generate a 120-package, ~1.5M-line program and measure `ceesafec check` and `build` (time, memory, C output size). Fix whatever breaks. | The port is 20× the largest CeeSafe program, and this is the biggest unknown. |
| Per-package incremental checking, with JSON diagnostics grouped by file | Compiler errors become a work queue for many agents at once, as with Bun's `cargo check` per crate. |
| Const generics (or an equivalent compile-time flag) | 1,409 const generic parameters (64% `bool`), mostly hot parser paths inherited from Zig's `comptime`. |
| Interior mutability (`Cell`, and a checked `RefCell` equivalent) | 791 `Cell`, 128 `RefCell`. |
| Pattern guards; default interface methods; decide on associated types and an iterator trait | Common in the translated code. Without them, every use gets rewritten by hand. |
| **Macro plan:** translation rules for the standard macros (`matches!`, `format!`/`write!`, `assert!`/`debug_assert!`, `vec!`, `unreachable!`, …), plus code generation for derives and Bun's own macros (`scoped_log!`, `pretty!`, `zstr!`, `declare_scope!`, host-function and binding attributes, …) | 37,247 invocations of 671 distinct macros. Watch for side effects inside `debug_assert!`, which caused one of Bun's regressions. |
| Threads alongside JavaScriptCore's garbage collector: check CeeSafe's data-race rules (ADR 0016) against Bun's thread pool and GC marker thread patterns | Threads in CeeSafe are new (accepted 2026-10-28). |
| Native Windows (ADR 0069) at Bun's needs | Bun supports Windows x64 and arm64. |
| A performance probe: Bun's hottest loops (lexer, hash, UTF-8) in CeeSafe against Rust | Overflow checks are always on in CeeSafe. Measure the cost early. |

**Exit:** the scale test checks and builds in acceptable time, and every gap above is either closed or has a written
translation rule.

**Progress (2026-11-09):** the scale test is `analysis/scale/scale_test.py`, and its findings are in
`analysis/scale/README.md`.
- **Fixed in the compiler (`fe4d0ca`):** three quadratic passes (C generation at 300k lines: 115 s → 16 s).
- **Open:** the single-file C build (one core: 21 minutes and 7.9 GB at 700k lines), split output that does not scale
  yet, and C functions declared in more than one package (128 in Bun).
- **The gaps' ADRs (2026-11-09, accepted as recommended):** `~/dev/CeeSafe/spec/decisions/0081`–`0087`.
  - **What they cover:** C declarations shared between packages, separate compilation at scale, const generic
    parameters, interior mutability, patterns, interfaces, and macros.
  - **How they were made:** each draft was written from Bun's measured usage and probes of the compiler. Two
    adversarial reviews and a fixer pass followed, with the evidence in `analysis/adr-evidence/`.
  - **Releases (2026-11-10):** all four are out, each implemented in worktrees, read by two adversarial reviewers,
    fixed, and checked by every suite, the bootstrap from 0.3.2 and the fixed point.
    - 0.24.3: ADR 0081's diagnostics, ADR 0082 stage A (split units per file, `--jobs`).
    - 0.25.0: ADR 0086 (interface defaults, associated types, `Iterator<T>`), ADR 0084 (cells), ADR 0085 step 1
      (guards, or-patterns, ranges, `@` bindings, constant patterns).
    - 0.26.0: ADR 0083 (const generics), ADR 0085 step 2 (string and slice patterns, `is`), ADR 0087 step 1
      (`debugAssert`, `c"…"`, `@derive`).
    - 0.27.0: ADR 0087 step 2 (constant `+`, `embed`/`embedText`).
  - **Still open in M0:** ADR 0082 stages B–F (stage D, per-package checking and `check --all`, is next), the threads
    and GC check, Windows at Bun's needs, and the performance probe.
  - **Windows (2026-11-10, a Windows 11 ARM64 VM with MSVC 14.51):** ceesafec builds with `cl` and reaches the fixed
    point there, but the corpus finds four Windows bugs that 0.27.0 already had (the release workflow never runs the
    corpus on Windows): `durable-files` and `file-append-metadata` panic, `CULong` is laid out as 8 bytes where Windows
    has 4 (`ffi/c-data`), and imported C enums are taken as unsigned where Windows makes them `int`
    (`ffi/imported-enums`).
- **Fixed in the compiler (`b7c9f41`):** a data race in safe code (`Share` was every `Send` type) and interface method
  bodies that were never checked. Both were found while drafting the ADRs.

### M1: Porting guide and trial (1 week)

- **`PORTING.md`:** Rust-to-CeeSafe mapping, written with Claude and reviewed adversarially.
  - Traits become interfaces; `dyn` stays `dyn`; closures become `fn` types and `Box<dyn fn>`.
  - Lifetimes become `borrow(a)` and regions; `Drop` becomes `drop {}`.
  - `Option` becomes `T?`; allocations become fallible.
  - Iterator chains become loops; macros follow the M0 plan; `unsafe` stays `unsafe` with `/// Safety:` lines.
- **`REGIONS.tsv`:** the Rust lifetimes of struct fields mapped to CeeSafe regions. It plays the role of Bun's
  `LIFETIMES.tsv`, and most of it can be read straight off the Rust types.
- **Trial:** port 3 representative files (one parser, one runtime binding, one `unsafe`-heavy I/O file), each with 1
  implementer, 2 adversarial reviewers and 1 fixer. Refine the guide.

**Exit:** the trial files compile, and reviewers find no systematic mistakes.

### M2: The proof slice, a CeeSafe `bun build` (4–6 weeks)

- **Scope:** core and platform plus transpiler and bundler: ~322,000 Rust lines, ~18% of Bun (1.4.4: ~297,000, 21%).
  - Core and platform: `bun_core`, collections, `sys`, `io`, `paths`, `threading`, …
  - Transpiler and bundler: `js_parser`, `js_printer`, `ast`, `bundler`, `resolver`, `css`, `sourcemap`, `parsers`,
    `md`, `glob`, …
- **Result:** a CeeSafe binary that transpiles and bundles.
- **Exit:**
  - Bun's bundler and transpiler tests pass (`test/bundler`, transpiler and CSS tests).
  - On the esbuild-style benchmarks (three.js bundle, transpile throughput), it stays within 10% of Rust Bun at the
    pin on Linux x64 and macOS arm64.

This milestone is the public proof: the same tests, the same benchmarks, Rust against CeeSafe.

### M3: The runtime (6–10 weeks)

- **Port:** the runtime (Node and Web APIs, JavaScriptCore glue, HTTP, SQL, Valkey, shell, test runner) and the
  package manager. The full `bun` binary then works.
- **Exit:**
  - `bun --version`, `bun run`, `bun test`, `bun install`, `bun build` and `bun serve` all work.
  - Bun's whole test suite passes on Linux x64.

### M4: All platforms (2–4 weeks)

- **Platforms:** Linux arm64, macOS x64 and arm64, Windows x64 and arm64.
- **Exit:** the whole test suite passes in CI on all six platforms, as Bun's rewrite did before merging.

### M5: The developer tools (4–6 weeks; can run in parallel with M3–M4)

- **Port:** the linter, type checker, formatter and React compiler: 744,000 lines (1.4.4: 621,000). They are
  self-contained compilers, the kind of code that ports fastest.
- **Exit:** their test suites (`src/lint/conformance`, `src/format/conformance`, the type checker's baselines) pass.

### M6: Performance parity and hardening (2–4 months)

- **Speed:** CeeSafe Bun within ±5% of Rust Bun at the pin on Bun's published benchmarks (`Bun.serve`, `node:http`,
  `next build`, `vite build`, `tsc -b`).
- **Size and memory:** binary size and memory use no worse.
- **Safety checks:** 24/7 fuzzing of the parsers, adversarial security review, and AddressSanitizer and
  LeakSanitizer through the C compiler.
- **Lol-html and argon2:** ported, or kept behind their C interfaces with a recorded reason.
- **Exit:** a CeeSafe Bun release candidate.

## 4. Estimates

The estimates scale Bun's 11 days by output size, then by 1.5–3× for a newer language: models know it less well, the
compiler has never seen code this large, and language features are missing. Our mail server port sets the floor of
that range.

| | Runtime only (M0–M4 and M6, without M5) | All of Bun (M0–M6) |
|---|---|---|
| Rust to port | ~840,000 lines without the AOT compiler (1.4.4: ~770,000) | ~1,790,000 lines (1.4.4: ~1,390,000) |
| CeeSafe written (about 1.2× Rust) | ~1.0 million | ~2.2 million |
| **Passes Bun's test suite** | **~2.5–4 months** | **~3–5 months** |
| **Releasable** | **~4.5–7 months** | **~5–9 months** |
| API cost (Bun's $165,000, scaled) | ~$0.3–0.6M | ~$0.5–1.0M |
| People | 1 engineer running the port, plus CeeSafe compiler work in parallel; both with agents | the same |
| Without agents (Bun's estimate of 3 engineers × 1 year, scaled) | ~4 engineer-years | ~8 engineer-years |

- **At the pin:** the times and costs above were estimated at 1.4.4 and are not rescaled. The Rust to port grew by
  about 9% for the runtime and 29% for all of Bun. The AOT compiler (210,000 lines, new since 1.4.4) is counted in
  "All of Bun" but in no milestone yet (§6).
- **Machine:** Bun's rewrite stalled on disk throughput and ran out of disk. Use many cores, at least 1 TB of fast
  storage and high IOPS.
- **Isolation:** cgroups for the stress tests.
- **CI:** six platforms.

## 5. Risks

| Risk | Mitigation |
|---|---|
| The compiler at 20× its largest program: compile time, memory, bugs, miscompiles | The M0 scale test comes first; compiler work runs alongside the port; a small differential test of compiled C against the interpreter |
| Agents write wrong CeeSafe more often than wrong Rust | `PORTING.md`, the CeeSafe MCP server (`check`, `explain`, `spec_search`), two adversarial reviewers per change, and fixing the workflow rather than the code |
| Performance: always-on overflow checks, bounds checks, fallible allocation | The M0 probe; M6 parity work; whole-program optimisation across CeeSafe's C and Bun's C++ |
| Macro translation errors (55k invocations) | Rules and code generation decided in M0; reviewers check macro sites against the Rust |
| Threads and the JS garbage collector under the data-race checker | Validated in M0; `unsafe` with `/// Safety:` lines where Bun's design needs it |
| Bun keeps moving: 97 commits and about 400,000 more Rust lines in the 19 days after 1.4.4 | A pinned `main` commit, moved only on purpose; the diff between pins is ported by hand for what is already ported; after M6, a catch-up loop |
| Windows | A native Windows check in M0, and the M4 platform milestone |

## 6. Decisions needed before M0

1. ~~**Scope:** runtime first (M5 later), or all of Bun?~~ Decided 2026-11-10: **runtime first**. M0–M4 and M6 come
   first (the "Runtime only" column of §4); M5, the developer tools, waits until the runtime is done.
2. ~~**Language changes:** which gaps get language changes (const generics, `Cell`, guards, default methods), and
   which get translation rules only.~~ Decided 2026-11-09: ADRs 0081–0087, accepted as recommended (CeeSafe `05beffb`).
   - **Language changes:** const generic parameters, cells, richer patterns, interface defaults and associated types,
     `@derive`, `debugAssert`, `c"…"` and `embed`.
   - **Translation rules only:** general macros, iterator chains, shared C declarations.
3. **Budget:** API spend (see the estimates) and the build machine.
4. ~~**Name and licence:** Bun is MIT. Keep the licence and credit, and decide the name of the port.~~ Decided
   2026-11-10:
   - **Licence:** decided 2026-11-10, **MIT, kept**, with Bun's copyright and credit. The port also keeps
     `upstream/LICENSE.md`'s notices for the code Bun links (JavaScriptCore and WebKit under LGPL-2, and the rest).
   - **Name:** decided 2026-11-10, **CeeBun**.
5. **The AOT compiler** (`src/aot`, 210,000 lines, new since 1.4.4): which milestone ports it. It checks a program and
   compiles it ahead of time (`bun compile`, and `--aot` for `bun run` and `bun test`), so it is part of the runtime's
   commands (M3), but it is a self-contained compiler like the developer tools (M5).

## 7. Next steps

1. ~~Check out Bun here as the frozen reference.~~ Done: `upstream/` (gitignored), a shallow clone. First at 1.4.4;
   moved on 2026-11-11 to the pinned `main` commit (§1): `git fetch --depth 1 origin
   89452d2ac13773aee8a6d632c4c30074bd1bb4fa && git checkout --detach FETCH_HEAD`.
2. ~~Start M0 with the compiler scale test.~~ Started: `analysis/scale/`.
3. Finish the scale test at 1.5 million lines, then draft the ADRs it calls for: separate compilation at scale, and C
   declarations shared between packages.
4. Draft the ADRs for the M0 language gaps.
