# CeeBun

CeeBun is a proof of concept that [Bun](https://bun.com)'s Rust can be ported to
[CeeSafe](https://github.com/CeeSafe/CeeSafe), a memory-safe systems language compiled to C. It is not a port of all
of Bun, and it stops at the proof.

**Status: done.** Two of Bun's crates, `bun_csrf` and `bun_zstd`, are replaced by CeeSafe inside Bun, with Rust and
CeeSafe linked into one binary. Bun's own tests for them pass in release and debug + ASAN builds, and the release
timings equal stock Bun's within noise ([`analysis/trials/`](analysis/trials/)). The work also measured Bun's Rust,
tested the CeeSafe compiler towards Bun's scale, and closed the language gaps it found (CeeSafe 0.24.3 to 0.32.0,
ADRs 0081–0088, 0090 and 0092). The core of Bun is not ported.

## What the proof shows

In one line: it supports "CeeSafe can replace Rust in Bun's leaf crates, at the same speed". It does not support
"CeeSafe is ready to port all of Bun" or "CeeSafe is faster than Rust".

### Readiness

Proven:

- **CeeSafe runs inside Bun.** `bun_csrf` and `bun_zstd` are CeeSafe, linked with Bun's Rust into one binary, and
  Bun's own tests for them pass in release and debug + ASAN builds.
- **The boundary works both ways.** Slices are lent for a call, and a `Vec<u8>` is handed to CeeSafe, grown there
  and handed back with no copy.
- **The embedding pieces are released.** CeeSafe starts without its own `main`, reports panics through Bun's crash
  handler, and allocates from Bun's allocator.
- **The gaps found were closed in the compiler,** not worked around. One accepted ADR, 0093 (unaligned reads and
  writes through a raw pointer), is deferred.

Not proven:

- **The core.** The foundation crates, the JavaScriptCore bindings, the event loop and the bundler are not ported.
  Crate-by-crate swapping stops at the foundation crates, so the core would have to be ported all at once.
- **Scale.** The compiler scale test completed at 707,000 lines. Bun's Rust is 1.79 million lines, and the
  1.5-million-line run was not completed ([`analysis/scale/README.md`](analysis/scale/README.md)).
- **Windows inside Bun.** The trial builds only for Unix targets.
- **Bun's Rust idioms at volume.** Two small crates and one function do not exercise the traits, generics, macros
  and async code the core is built from.

### Efficiency

Proven:

- **Equal to Rust, not faster.** On Bun's wyhash, safe CeeSafe matches Bun's unsafe-tuned Rust from 1 KB up and is
  12–16% slower on short keys. Written with the same unchecked reads as Rust, short keys come within 2–5%.
- **No measurable cost at the boundary.** `bun_zstd`'s release timings equal stock Bun's within noise, and the
  binary is 16.5 KB larger.
- **Not dependent on the C compiler for wide multiplies.** Since ceesafec 0.32.0 the hash is equal to Rust with
  Apple clang 21 too, where it had been 2.5 to 3.8 times slower.

Not proven:

- **One function is one data point.** It is an arithmetic loop. Nothing was measured for allocation-heavy code,
  hash maps, string handling, async, the parser or the bundler.
- **Not measured inside Bun.** There the Rust hash is force-inlined into every hash-map lookup; the wyhash
  comparison ran in a standalone harness.
- **Safe code has a cost on short inputs.** The bounds checks on short keys were the 12–16%; matching Rust there
  took unchecked reads.

The reports are in [`analysis/trials/`](analysis/trials/), the code in
[CeeSafe/ceebun-trial](https://github.com/CeeSafe/ceebun-trial), and the plan a full port would follow, which is not
planned, in [`ROADMAP.md`](ROADMAP.md).

## Contents

- [`ROADMAP.md`](ROADMAP.md): the plan, with the measurements, the milestones (M0–M6), the estimates, the risks and the
  decisions taken. Read it first.
- [`analysis/`](analysis/): the scripts behind the measurements.
  - `bun_census.py` and `bun_rust_features.py`: lines and Rust feature counts.
  - `probes/`: small programs testing which Rust features CeeSafe supports.
  - `scale/`: the compiler scale test and its report.
  - `trials/`: the reports of the two crates swapped inside Bun, `bun_csrf` and `bun_zstd`, and of the wyhash timing
    against Rust.
  - `adr-evidence/`: the evidence for CeeSafe ADRs 0081–0088 and 0090.
- [`CLAUDE.md`](CLAUDE.md): instructions for the agents doing the port.

## The Bun reference

The port follows Bun file by file, at a pinned commit of Bun's `main`: `89452d2ac137` (2026-11-10), 97 commits after
1.4.4 (`ROADMAP.md` §1). Bun is not vendored here; check it out as `upstream/`:

```sh
git init upstream && cd upstream
git remote add origin https://github.com/oven-sh/bun.git
git fetch --depth 1 origin 89452d2ac13773aee8a6d632c4c30074bd1bb4fa && git checkout --detach FETCH_HEAD
```

Then run the analyses, for example `python3 -I analysis/bun_census.py upstream`.

## Licence

MIT, as Bun is: see [`LICENSE`](LICENSE). The libraries Bun links, such as JavaScriptCore and WebKit, keep their own
licences: see [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md). CeeBun is an independent port, not affiliated with
or endorsed by Oven.
