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
