# Porting Bun to CeeSafe: roadmap

**Goal:** show that CeeSafe can replace Rust, by porting Bun 1.4.4 (Rust) to CeeSafe. The port must pass Bun's own
test suite and match its performance.

**Status:** planning (2026-11-09). Nothing is ported yet.

## 1. Starting point

### Bun 1.4.4

- **Release:** tag `bun-v1.4.4`, commit `38afee6c84fc`, 2026-10-22.
- **Rust:** about 1.39 million lines, not counting blanks or comments, in 3,221 files and 122 crates. Only about 22,000
  lines are generated.

| Part of Bun | Rust lines | Share |
|---|---|---|
| Developer tools: linter (`src/lint`), type checker (`src/sema`), formatter (`src/format`), React compiler | 621,933 | 44.7% |
| Runtime: Node and Web APIs, JavaScriptCore glue, servers, SQL, shell, test runner | 344,652 | 24.8% |
| Transpiler and bundler: parser, printer, AST, bundler, resolver, CSS, source maps, YAML/TOML/Markdown | 208,547 | 15.0% |
| Package manager: `bun install`, semver, patch | 96,273 | 6.9% |
| Core and platform: allocators, collections, I/O, event loop, threads, system calls, uWS glue | 88,592 | 6.4% |
| Other small crates | 31,214 | 2.2% |

- **Not ported:** about 230,000 lines of C++ (mostly the JavaScriptCore bindings in `src/jsc`) and about 190,000 lines
  of C. Neither is ported: CeeSafe calls the same `extern "C"` functions Rust calls today.
- **Native libraries:** JavaScriptCore, BoringSSL, usockets/uWS, lsquic, SQLite, zlib, zstd, brotli, mimalloc,
  libuv and c-ares are linked unchanged. Two are Rust: **lol-html** (`HTMLRewriter`) and **rust-argon2**. They stay
  linked through their C interfaces until they are ported.
- **Third-party crates:** 25 are runtime dependencies, and 11 of them exist only for macros (`syn`, `quote`, `paste`,
  `strum`, `thiserror`, `bitflags`, …). The others are small: `encoding_rs`, `hashbrown`, `smallvec`, `bcrypt`,
  `blake2`, `sha3`, `rustix`, `libc`, `bstr`, `itoa`, …
- **The tests:** about 60,000 tests and 1.4 million assertions, written in TypeScript. They don't depend on the
  language Bun is written in, so they are the oracle for the port.

### How Bun's Rust is written

Measured over the hand-written Rust:

| Feature | Count | Per 1,000 lines |
|---|---|---|
| `unsafe` blocks, functions and impls | 12,835 | 9.4 |
| Raw pointer types | 12,964 | 9.5 |
| `extern "C"` items | 1,642 | 1.2 |
| Generic functions and types | 15,088 | 11.0 |
| Trait impls / trait definitions | 5,082 / 540 | 3.7 / 0.4 |
| `dyn` uses / `Box<dyn Fn>` and `impl Fn` | 717 / 1,009 | |
| Macro invocations (671 distinct macros) | 37,247 | 27.2 |
| `macro_rules!` definitions | 707 | |
| Const generics and `const fn` | 1,607 | |
| `Cell` / `RefCell` | 1,016 | |
| Thread and atomic sites | 1,516 | |
| async/await | 2 | none in practice |
| SIMD / inline asm | 18 / 15 | |

The code is a faithful port from Zig, with the same architecture and data structures, and it was made with AI agents.
That shows in the heavy use of `unsafe` and raw pointers.

### CeeSafe 0.21.0 against what Bun uses

Each line below was tested with a small program on the installed compiler (`ceesafec run --interp`), unless marked
otherwise.

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
  1.7 million, **20 times larger**.

## 2. Approach

1. **A faithful, mechanical port of Rust to CeeSafe.** Same architecture, same data structures, same files. Idiomatic
   cleanup comes after the port works, as Bun did after its Zig port.
2. **All at once, not incrementally**, as Bun's blog recommends. Rust crates call each other through Rust types, so a
   mixed Rust/CeeSafe build would need temporary glue everywhere.
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
| Const generics (or an equivalent compile-time flag) | 1,607 uses, mostly hot parser paths inherited from Zig's `comptime`. |
| Interior mutability (`Cell`, and a checked `RefCell` equivalent) | 1,016 uses. |
| Pattern guards; default interface methods; decide on associated types and an iterator trait | Common in the translated code. Without them, every use gets rewritten by hand. |
| **Macro plan:** translation rules for the standard macros (`matches!`, `format!`/`write!`, `assert!`/`debug_assert!`, `vec!`, `unreachable!`, …), plus code generation for derives and Bun's own macros (`scoped_log!`, `pretty!`, `zstr!`, `declare_scope!`, host-function and binding attributes, …) | 37,247 invocations of 671 distinct macros. Watch for side effects inside `debug_assert!`, which caused one of Bun's regressions. |
| Threads alongside JavaScriptCore's garbage collector: check CeeSafe's data-race rules (ADR 0016) against Bun's thread pool and GC marker thread patterns | Threads in CeeSafe are new (accepted 2026-10-28). |
| Native Windows (ADR 0069) at Bun's needs | Bun supports Windows x64 and arm64. |
| A performance probe: Bun's hottest loops (lexer, hash, UTF-8) in CeeSafe against Rust | Overflow checks are always on in CeeSafe. Measure the cost early. |

**Exit:** the scale test checks and builds in acceptable time, and every gap above is either closed or has a written
translation rule.

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

- **Scope:** core and platform plus transpiler and bundler: ~300,000 Rust lines, ~22% of Bun.
  - Core and platform: `bun_core`, collections, `sys`, `io`, `paths`, `threading`, …
  - Transpiler and bundler: `js_parser`, `js_printer`, `ast`, `bundler`, `resolver`, `css`, `sourcemap`, `parsers`,
    `md`, `glob`, …
- **Result:** a CeeSafe binary that transpiles and bundles.
- **Exit:**
  - Bun's bundler and transpiler tests pass (`test/bundler`, transpiler and CSS tests).
  - On the esbuild-style benchmarks (three.js bundle, transpile throughput), it stays within 10% of Rust Bun 1.4.4 on
    Linux x64 and macOS arm64.

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

- **Port:** the linter, type checker, formatter and React compiler: 622,000 lines. They are self-contained compilers,
  the kind of code that ports fastest.
- **Exit:** their test suites (`src/lint/conformance`, `src/format/conformance`, the type checker's baselines) pass.

### M6: Performance parity and hardening (2–4 months)

- **Speed:** CeeSafe Bun within ±5% of Rust Bun 1.4.4 on Bun's published benchmarks (`Bun.serve`, `node:http`,
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
| Rust to port | ~770,000 lines | ~1,390,000 lines |
| CeeSafe written (about 1.2× Rust) | ~0.9 million | ~1.7 million |
| **Passes Bun's test suite** | **~2.5–4 months** | **~3–5 months** |
| **Releasable** | **~4.5–7 months** | **~5–9 months** |
| API cost (Bun's $165,000, scaled) | ~$0.3–0.6M | ~$0.5–1.0M |
| People | 1 engineer running the port, plus CeeSafe compiler work in parallel; both with agents | the same |
| Without agents (Bun's estimate of 3 engineers × 1 year, scaled) | ~4 engineer-years | ~8 engineer-years |

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
| Macro translation errors (37k invocations) | Rules and code generation decided in M0; reviewers check macro sites against the Rust |
| Threads and the JS garbage collector under the data-race checker | Validated in M0; `unsafe` with `/// Safety:` lines where Bun's design needs it |
| Bun keeps moving (version 1.4.4 now, more later) | Freeze at 1.4.4; after M6, a catch-up loop that ports upstream changes |
| Windows | A native Windows check in M0, and the M4 platform milestone |

## 6. Decisions needed before M0

1. **Scope:** runtime first (M5 later), or all of Bun?
2. **Language changes:** which gaps get language changes (const generics, `Cell`, guards, default methods), and which
   get translation rules only.
3. **Budget:** API spend (see the estimates) and the build machine.
4. **Name and licence:** Bun is MIT. Keep the licence and credit, and decide the name of the port.

## 7. Next steps

1. ~~Check out Bun 1.4.4 here as the frozen reference.~~ Done: `upstream/` (gitignored), a shallow clone made with
   `git clone --depth 1 --branch bun-v1.4.4 https://github.com/oven-sh/bun.git upstream`.
2. Start M0 with the compiler scale test.
3. Draft the ADRs for the M0 language gaps.
