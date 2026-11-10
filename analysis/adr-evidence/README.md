# Evidence for ADRs 0081–0087

The CeeSafe ADRs raised by M0 (`~/dev/CeeSafe/spec/decisions/0081-…` to `0087-…`) quote counts measured on Bun 1.4.4,
and behaviour measured on ceesafec 0.24.2 (`fe4d0ca`). This folder keeps what produced them, so each number can be
measured again. There is one folder per ADR:

- **Counting scripts (`*.py`):** each reads Bun's source. Run them with `python3 -I <script> upstream` (or as the
  script's docstring says) from the repository's root.
- **Probes (`*.cee`, small packages):** each checks one behaviour of the compiler. Run them with
  `ceesafec check|run --interp|build`.
- **Saved output (`census*.txt`):** some folders also keep the output the ADR quotes.

The generated programs from the scale test are not kept: `analysis/scale/scale_test.py` makes them again.

**ADR 0088** (embedding CeeSafe in a host program) was raised by the `bun_csrf` trial (`analysis/trials/csrf/REPORT.md`)
and measured on ceesafec 0.27.0. Its folder has one script, `0088/run.sh`, which builds every probe (C hosts, a Rust
host, two-object links, ELF links with ld.lld, ThreadSanitizer and UBSan runs) and prints what the ADR quotes; run it
with `bash`. `0088/results.txt` is its output on the Mac (Apple clang 21, arm64, LLD 21). `0088/bun/panic_in_bun.log` is
the trial's own output for a deliberate panic, copied, not remade. Its build products are ignored (`0088/.gitignore`).
