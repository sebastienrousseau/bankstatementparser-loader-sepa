# Benchmarks

`benches/bench_load_sepa.py` measures what a SEPA message costs to load
as it grows in transactions, for the two messages this loader reads: a
PAIN.008 collection (`DrctDbtTxInf` records in `PmtInf` blocks of 500)
and a PAIN.002 status report (`TxInfAndSts` records, alternately
settled and rejected with a reason code). It times `load_sepa` and,
beside it, `summarize_sepa`, which parses the same XML but builds no
`Transaction` objects.

Each figure is the best of 5 runs after one untimed warm-up. Nothing
asserts a threshold: wall-clock is not comparable between machines. CI
runs `python benches/bench_load_sepa.py --quick` on every push so the
benchmark keeps running against the current API.

## Results

Run with `poetry run python benches/bench_load_sepa.py` on 2026-11-27:
Apple M1 Pro, macOS 27.2.1, CPython 3.12.16,
bankstatementparser-loader-sepa 0.0.36, bankstatementparser 0.0.35,
defusedxml 0.7.1.

| Message | Transactions | KiB | `load_sepa` ms | `summarize_sepa` ms | us per transaction |
| :--- | ---: | ---: | ---: | ---: | ---: |
| PAIN.008 | 10 | 3.5 | 0.20 | 0.17 | 19.82 |
| PAIN.008 | 100 | 32.5 | 1.72 | 1.56 | 17.19 |
| PAIN.008 | 1000 | 327.1 | 17.37 | 15.77 | 17.37 |
| PAIN.008 | 10000 | 3317.1 | 210.74 | 183.68 | 21.07 |
| PAIN.008 | 50000 | 16762.8 | 1148.20 | 1143.56 | 22.96 |
| PAIN.002 | 10 | 1.9 | 0.15 | 0.14 | 15.43 |
| PAIN.002 | 100 | 18.0 | 1.40 | 1.24 | 14.02 |
| PAIN.002 | 1000 | 180.2 | 14.35 | 13.46 | 14.35 |
| PAIN.002 | 10000 | 1818.3 | 192.34 | 140.15 | 19.23 |
| PAIN.002 | 50000 | 9138.3 | 1297.52 | 851.32 | 25.95 |

From 10 to 50,000 transactions the cost per transaction rises 1.16x
for PAIN.008 and 1.68x for PAIN.002, most of it above 10,000
transactions. No code path rescans the document per transaction: each
lookup walks one transaction's own subtree. `summarize_sepa` costs
between 0.66x and 1.00x `load_sepa`: both parse the whole document,
which dominates, and the summary saves only the `Transaction` objects.

Reproduce with `python benches/bench_load_sepa.py` (add `--json` for
machine-readable output).
