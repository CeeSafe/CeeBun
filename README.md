# CeeBun

CeeBun is a proof of concept that [Bun](https://bun.com)'s Rust can be ported to
[CeeSafe](https://github.com/CeeSafe/CeeSafe), a memory-safe systems language compiled to C. It is not a port of all
of Bun, and it stops at the proof.

**Status: done.** Two of Bun's crates, `bun_csrf` and `bun_zstd`, are replaced by CeeSafe inside Bun, with Rust and
CeeSafe linked into one binary. Bun's own tests for them pass in release and debug + ASAN builds, and the release
timings equal stock Bun's within noise ([`analysis/trials/`](analysis/trials/)). The work also measured Bun's Rust,
tested the CeeSafe compiler at Bun's scale, and closed the language gaps it found (CeeSafe 0.24.3 to 0.31.0, ADRs
0081–0088 and 0090). The core of Bun is not ported: [`ROADMAP.md`](ROADMAP.md) says what the proof does and does not show.

## Contents

- [`ROADMAP.md`](ROADMAP.md): the plan, with the measurements, the milestones (M0–M6), the estimates, the risks and the
  decisions taken. Read it first.
- [`analysis/`](analysis/): the scripts behind the measurements.
  - `bun_census.py` and `bun_rust_features.py`: lines and Rust feature counts.
  - `probes/`: small programs testing which Rust features CeeSafe supports.
  - `scale/`: the compiler scale test and its report.
  - `trials/`: the reports of the two crates swapped inside Bun, `bun_csrf` and `bun_zstd`.
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
