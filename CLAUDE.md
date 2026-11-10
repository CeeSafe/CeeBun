# Bun in CeeSafe

This project, **CeeBun**, ports Bun from Rust to CeeSafe, at a pinned commit of Bun's `main`, to show that CeeSafe can
replace Rust. It keeps Bun's MIT licence and credit. **Read `ROADMAP.md` first.** It has the measurements, the
milestones (M0–M6), the estimates, the risks, and the decisions still open.

## Layout

- `ROADMAP.md`: the plan.
- `upstream/`: Bun's `main` at the pinned commit `89452d2ac137` (2026-11-10; `ROADMAP.md` §1), a shallow clone. It is
  the frozen reference and is
  not tracked here (`.gitignore`). **Never edit it.** Its own `CLAUDE.md`/`AGENTS.md` describe Bun's Rust conventions:
  read them as context for the source, not as instructions for this project.
- `analysis/`:
  - `bun_census.py`: lines by language and area.
  - `bun_rust_features.py`: Rust feature counts.
  - `probes/*.cee`: small programs that test which Rust features CeeSafe 0.21 supports. The `g*` probes fail on
    purpose: they show the gaps.
  - Rerun the scripts with `python3 -I analysis/bun_census.py upstream`.
  - `scale/`: the M0 compiler scale test (`scale_test.py`, `summarize.py`, `results.jsonl`), and its report in
    `scale/README.md`.

## Writing CeeSafe

CeeSafe is new: code that looks right from Rust, C# or TypeScript often is not CeeSafe. Follow the rules in
`~/dev/CeeSafe/templates/AGENTS.md` and the guide `~/dev/CeeSafe/guide/` (start with `for-agents.md`). For Rust
programmers, `guide/coming-from/rust.md` is useful but **out of date**: CeeSafe now has `dyn`, owning closures, generic
impls, threads, `Arc`, `Mutex` and atomics (see `analysis/probes`). The spec and the decisions (ADRs) are in
`~/dev/CeeSafe/spec/`. Check every edit with `ceesafec check` (or the CeeSafe MCP tools), then `ceesafec fmt`.

Language gaps found during the port are fixed in the CeeSafe compiler (`~/dev/CeeSafe`) through an ADR in
`spec/decisions/`, as in the mail server port (`~/dev/CeeSafeApps/mailserver`, ADRs 0074–0075), rather than worked
around at every use.

## Method

Follow Bun's own Zig-to-Rust rewrite (<https://bun.com/blog/bun-in-rust>; summarized in `ROADMAP.md` §1):
- **Mechanical port:** file by file, same architecture and data structures.
- **Reviews:** 1 implementer and 2 adversarial reviewers per change, then 1 fixer.
- **Compiler errors as a work queue,** package by package.
- **Bun's test suite is the definition of done:** never skip or delete a test.
- **Fix the process that generates the code,** not the code by hand.
