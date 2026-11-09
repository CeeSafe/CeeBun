# M0: the compiler scale test

The first M0 item of `ROADMAP.md`: can `ceesafec` take a program of Bun's size? The port will be about 1.7 million
lines in about 120 packages, 20 times the largest CeeSafe program so far (the compiler, 85,000 lines).

**Status (2026-11-09):** started. Three quadratic passes found and fixed in the compiler (`~/dev/CeeSafe`
commit `fe4d0ca`, on main). The gaps it found have ADRs (0081–0087, Proposed, `101d7bb`). The remaining blocker is the C step: the whole
program is one C file compiled on one core, and split output is not yet usable at this scale.

## The test

`scale_test.py` generates a program shaped like Bun and measures `ceesafec` on it:

- **Packages:** `--packages` libraries in a layered graph. Each depends on `p000` (like `bun_core`) and on up to 4 other
  earlier ones. One executable, `app`, depends on all of them.
- **Files:** about 470 lines each (Bun's average is 430). Each holds four units of the code a mechanical port of Bun's
  Rust produces:
  - structs with methods, and an enum with payloads matched by `match`;
  - an interface with a generic impl, and `dyn` dispatch;
  - stored owning closures, `Vector` and `HashMap`, string building and fallible allocation;
  - an `unsafe` FFI call.
- **Steps measured:** `check`; `build --emit c`; the full `build`; and, with `--split`, split C compiled in parallel
  with one job per CPU. For each it records wall time, CPU time, peak memory and the size of the C. It runs the binary,
  and with `--interp` compares its output with the interpreter's.

```sh
python3 -I analysis/scale/scale_test.py --lines 300000 --packages 120 [--split] [--interp] [--out out/scale]
python3 -I analysis/scale/summarize.py          # results.jsonl as a table
```

Results go to `results.jsonl`, one JSON line per run. `compiler_path` tells the release apart from a branch build,
because both report version 0.24.2.

## Results

**Machines:**
- **MacBookPro:** macOS 27, arm64, 8 cores, 16 GB, Apple clang 21.
- **hanan:** Debian 12, x86-64, 12 cores, 31 GB, gcc 12.2. Runs there are capped by a 12 GB cgroup, because the box
  runs other services.

Every build ran and printed the same result. At 5k and 27k lines, the interpreter's output matched the binary's.

**ceesafec 0.24.2, the release:**

| Host | Lines | check | emit C | C | build (with the C compiler) |
|---|---|---|---|---|---|
| Mac | 26,844 | 0.33 s | 1.84 s | 9.7 MB | 18.3 s, 0.5 GB |
| Mac | 102,469 | 1.29 s | 14.97 s | 36.8 MB | 52.0 s, 1.0 GB |
| Mac | 304,176 | 5.22 s | 113.67 s | 109.5 MB | 228.1 s, 2.8 GB |
| hanan | 304,176 | 7.45 s | 130.96 s | 109.5 MB | 333.2 s, 3.2 GB |
| hanan | 707,469 | 28.09 s | 708.9 s | 255.4 MB | 1,287 s, 7.9 GB |

The 1.5-million-line run with the release was stopped while it was still generating C. The 300k and 700k rows already
show the curve: C generation grows about as the square of the size, and would take about 40 minutes at 1.5M.

**With the fixes, `fe4d0ca` (the same C, byte for byte):**

| Host | Lines | check | emit C | build, one C file | build, split, 8 jobs |
|---|---|---|---|---|---|
| Mac | 25,000 | 0.29 s | 1.20 s | | |
| Mac | 100,000 | 1.15 s | 4.53 s | | |
| Mac | 304,176 | 3.49 s | 15.60 s | 134.9 s, 1.7 GB | 30.9 s emit + 68.9 s cc (199.6 s CPU) |
| Mac | 707,469 | 12.6 s | 58.39 s | | |

| hanan | 304,176 | 6.0 s | 22.3 s | 224.7 s, 3.1 GB | 25.8 s emit + 292.5 s cc (2,353 CPU-s, 12 jobs) |
| hanan | 707,469 | | | | killed: the 12 GB cgroup ran out of memory in gcc (`cc1`) |

The hanan runs are in `/root/bun-scale/results.jsonl` on that box:
- **Split, 300k:** with gcc, the parallel split build is *slower* than one file, and uses ten times the CPU. Each of
  the 12 units parses the 54.7 MB shared header.
- **700k:** with 12 jobs, the units did not fit in 12 GB, and the kernel's out-of-memory killer stopped the ramp, so
  the 1.5M run never started. The release builds 700k as one file in 7.9 GB.

Today's split output is no way out at this size: the shared header must go (ADR 0082).

## Findings

1. **The same C function cannot be declared in two packages** (N0201, "the C name … is already used").
   - **In Bun:** the crates declare 128 of their 2,819 C functions more than once, mostly BoringSSL, libuv and
     kqueue calls.
   - **The decision:** either an ADR allowing identical redeclarations across packages (Rust's rule: one symbol, and the
     signatures must agree), or a translation rule moving each shared declaration into one package.
   - **For now:** the scale test declares the function in `p000` and calls a `public unsafe fn`.
2. **C generation was quadratic: fixed.** All three passes were in the compiler:
   - `aggregateEnumNamed` named every aggregate type for each variant value.
   - Each `Drop`, `BoxFree` and placement site allocated a `Vector<bool>` the size of the type table.
   - The checker scanned every replaced qualified name for each identifier. This one also slows `check`, and a port
     full of `dep.item` names makes it worse.

   At 300k lines, C generation went from 115.5 s to 15.6 s, and `check` from 5.4 s to 3.5 s. The output stays
   byte-identical. Every contract test, the corpus and two adversarial reviews (1,285 inputs compared) pass.
   - **Still superlinear:** C generation grew 3.7 times from 300k to 700k lines, for 2.3 times the code. The next hot
     spot is `setUpEmitter`'s own loops: 3.4% of the samples at 300k, 17.6% at 700k.
3. **The C compiler is now the bottleneck.**
   - **One file:** without `--split`, the whole program is one `main.c`. That is 255 MB at 700k lines, and about
     540 MB is expected at 1.5M.
   - **One core:** the C compiler runs on one core. At 700k lines, gcc took 21 minutes and 7.9 GB.
   - **Degraded warnings:** gcc turns off column tracking for warnings in files this large.
4. **`--split` exists (ADR 0022) but doesn't scale yet:**
   - **No parallelism:** `ceesafec build --split` passes every unit to one C compiler call
     (`src/host/toolchain.cee`), which compiles them one after another.
   - **Units merge:** files with the same name in different packages become one unit (`f000.c` holds every package's
     `f000.cee`). c-backend.md §2.4 promises one unit per source file. Bun has a `lib.rs` in every crate and many
     `mod.rs` files, so most of its units would merge. At 300k lines, 2,500 source units became 12 C units.
   - **The header:** `ceesafe_program.h` holds the types, prototypes and `static inline` helpers of the whole program,
     and every unit includes it. At 300k lines it is 54.7 MB, half of all the C. With one unit per file, a Bun-sized
     program would parse a header of most of the program once for each of about 3,000 units.

   Even so, compiling the split units in parallel cut the 300k C step from about 120 s to 69 s on 8 cores.
   - **Needed:** separate compilation designed for scale (an ADR):
     - units per package and per file that never merge;
     - per-unit headers with only what each unit uses;
     - `--jobs`;
     - a cache, so a change rebuilds only its own units.

     This is also what lets agents rebuild a package without rebuilding the program.
5. **The language server repeats finding 2's checker scan:** `src/tooling/semantic_index.cee:298` scans every
   replaced identifier for each identifier. It is not fixed yet.

## Next

- Measure the branch at 700k and 1.5M lines on hanan; record peak memory against the 12 GB cap.
- Profile and fix `setUpEmitter`'s remaining superlinear loops, and the same scan in the language server.
- Draft two ADRs: separate compilation at scale (finding 4), and C declarations shared between packages (finding 1).
- Per-package incremental checking with JSON diagnostics, the next M0 item, depends on the first of these ADRs.
