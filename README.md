# CeeBun

CeeBun ports [Bun](https://bun.com) 1.4.4 from Rust to [CeeSafe](https://github.com/CeeSafe/CeeSafe), a memory-safe
systems language compiled to C. The goal is to show that CeeSafe can replace Rust: the port must pass Bun's own test
suite and match its performance.

**Status:** milestone M0 (readiness). Nothing of Bun is ported yet. The work so far has measured Bun's Rust, tested the
CeeSafe compiler at Bun's scale, and closed the language gaps it found (CeeSafe 0.24.3 to 0.27.0, ADRs 0081–0087).

## Contents

- [`ROADMAP.md`](ROADMAP.md): the plan, with the measurements, the milestones (M0–M6), the estimates, the risks and the
  decisions taken. Read it first.
- [`analysis/`](analysis/): the scripts behind the measurements.
  - `bun_census.py` and `bun_rust_features.py`: lines and Rust feature counts.
  - `probes/`: small programs testing which Rust features CeeSafe supports.
  - `scale/`: the compiler scale test and its report.
  - `adr-evidence/`: the evidence for CeeSafe ADRs 0081–0087.
- [`CLAUDE.md`](CLAUDE.md): instructions for the agents doing the port.

## The Bun reference

The port follows Bun 1.4.4 file by file. Bun is not vendored here; check it out as `upstream/`:

```sh
git clone --depth 1 --branch bun-v1.4.4 https://github.com/oven-sh/bun.git upstream
```

Then run the analyses, for example `python3 -I analysis/bun_census.py upstream`.

## Licence

MIT, as Bun is: see [`LICENSE`](LICENSE). The libraries Bun links, such as JavaScriptCore and WebKit, keep their own
licences: see [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md). CeeBun is an independent port, not affiliated with
or endorsed by Oven.
