# Changelog

All notable changes to `bankstatementparser-loader-sepa` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.36] - 2026-11-27

### Fixed

- An amount is read only when it is an ISO 20022 decimal (ASCII
  digits with an optional fraction); anything else is `0.00`, the
  existing fallback for text that is not a number. Before, `NaN` and
  `Infinity` reached `Transaction` and failed its validation, `sNaN`
  escaped `load_sepa` and `summarize_sepa` as
  `decimal.InvalidOperation`, the summary could total `NaN` or
  `Infinity`, and `1e5`, `1_000`, a sign or other scripts' digits were
  loaded as numbers.
- The README described fields the loader does not have
  (`summary.group_status`, `accepted_count`, `rejected_count`), group
  status parsing it does not do, and reason codes stored in references
  (they are in the description). It now documents the element mapping
  and the defaults as the code applies them, and
  `tests/test_docs_accuracy.py` checks the Quick Start, the defaults
  and the two documented errors.

### Added

- An Atheris fuzz target, `fuzz/fuzz_load_sepa.py`, for `load_sepa`
  and `summarize_sepa`, with a seed corpus; it fails on any exception
  but `ParseError` and `defusedxml`'s refusal, on a malformed
  `Transaction`, and on a summary that disagrees with the load. CI
  runs it for 120 s on every change; `make fuzz` locally.
- `benches/bench_load_sepa.py`, a real benchmark of `load_sepa` and
  `summarize_sepa` on PAIN.008 collections and PAIN.002 reports of 10
  to 50,000 transactions, replacing a file that timed an empty loop.
  CI runs `--quick`; `docs/BENCHMARKS.md` records a full run with its
  environment.
- `tests/fixtures/pain008.xml` and `pain002.xml`, a collection and its
  status report, with golden tests.
- A `Makefile` wrapping the local gates (`make check`).
- A MkDocs Material user manual (`mkdocs.yml`, `docs/`) with an
  mkdocstrings API reference, built with `--strict` on every pull
  request and deployed to GitHub Pages from `main`
  (`.github/workflows/docs.yml`, `make docs`). It replaces a Sphinx
  configuration that nothing built.
- `ARCHITECTURE.md`, `CODE_OF_CONDUCT.md`, `docs/POLICIES.md`,
  `docs/BENCHMARKS.md`, `docs/COMPARISON.md`, `docs/format.md` and
  `docs/suite.md`.
- Signed releases: keyless cosign `.sig` and `.pem` per distribution,
  SLSA provenance
  (`bankstatementparser-loader-sepa-vX.Y.Z.intoto.jsonl`,
  slsa-github-generator 2.1.0), CycloneDX and SPDX SBOMs and a licence
  manifest on every GitHub release, and PEP 740 attestations on PyPI.
- The OpenSSF Scorecard workflow, the suite's Docs Lint workflow
  (`scripts/readme-check.sh` and markdownlint), a Security workflow
  (Bandit and `pip-audit` on every locked set), the portfolio pull
  request and issue templates, and `.github/demo.gif` rendered by
  `make demo` from `.github/demo.tape`.
- Hash-pinned requirement sets exported from the lock
  (`requirements/{runtime,ci,fuzz,docs}.txt`, by the suite's
  `scripts/export_locked_requirements.py`) and compiled release tooling
  (`requirements/{build,sbom}.txt`).

### Changed

- Require `bankstatementparser >= 0.0.35`, the newest core release, and
  align the version with the suite's 0.0.36 release; `poetry.lock`
  moves core to 0.0.35.
- Dev tools: ruff 0.17.6, mypy 2.4.1, pytest 9.2.0, hypothesis 6.168.5,
  tomli 2.5.0 and pytest-benchmark 5.3.1 (Dependabot #4 to #9).
- CI pins every action by commit SHA, installs only the hashed lock
  exports, and tests CPython 3.10 to 3.14 on Ubuntu, macOS and Windows.
  Write permissions sit on the jobs that need them.
- The examples load a PAIN.008 collection and its PAIN.002 report,
  with a rejection, and use the parser plugin.
- `README.md` follows the portfolio template. The suite table moves to
  `docs/suite.md`. `CONTRIBUTING.md` describes the steps that work in
  this repository.

## [0.0.35] - 2026-11-26

The first release on PyPI. Versions 0.0.20 to 0.0.34 were never
released: the package joins the bankstatementparser suite, which ships
one version across every package, at 0.0.35.

### Added

- `.github/workflows/release.yml`: a `v*` tag builds the sdist and
  wheel, publishes them to PyPI by trusted publishing, attaches them to
  a GitHub release and writes its notes with `scripts/release_notes.py`
  from the highlights in `.github/releases/<tag>.md`.
- `.github/workflows/pr.yml` (PR Gate) and
  `.github/workflows/suite-consistency.yml`, a daily check that every
  suite package on PyPI agrees on one version
  (`scripts/check_suite_consistency.py`).
- `scripts/verify_versions.py` and the suite's shared
  `tests/test_suite_conformance.py` and `tests/test_release_notes.py`.
- `.github/dependabot.yml`: weekly pip and GitHub Actions updates.
- `scripts/check_complexity.py`, the suite's complexity gate, with
  `scripts/complexity_baseline.json`: per-function ceilings
  (cyclomatic 10, cognitive 15, Halstead 30, 60 lines; 500 lines per
  file), run in CI's lint job. Functions already over a ceiling are
  baselined and may not get worse.
- `.github/workflows/codeql.yml`: CodeQL as an advanced setup for
  Python and GitHub Actions, on pushes and pull requests to `main`
  and weekly.

### Changed

- **Breaking:** `get_summary()` returns `total_amount` as `Decimal`, as the core
  `SummaryRecord` declares, instead of `float`. The value is exact, summed from the
  amounts parsed out of the message text. Code comparing it with a float literal
  must compare with a `Decimal` instead: `Decimal("89.90") == 89.90` is `False`.
- Requires `bankstatementparser >= 0.0.34` (was `>= 0.0.18`).
- PAIN.002 and PAIN.008 transactions find their amount and currency
  through one helper, `_find_amount`. Behaviour is unchanged; two
  branches that no input could reach are gone, and both callers are
  within the suite's complexity ceilings.
- The coverage gate measures branches (`--cov-branch`); coverage is
  100% with branches counted.
- Dev dependency floor `pytest >= 9.0.3`, the release that fixes
  PYSEC-2026-1845; `tomli` (Python < 3.11) and `packaging` declared for
  the conformance test.
- GitHub Actions: `actions/checkout` v7, `actions/setup-python` v7.
- `_parse_sepa_xml` is split into small helpers so every function is
  under the complexity ceilings. Output is unchanged, pinned by
  characterisation tests.

### Fixed

- `get_summary()` returns `SepaSummaryRecord`, a `SummaryRecord` subtype, so the
  override matches the core parser's contract and `mypy` passes against
  bankstatementparser 0.0.29.

## [0.0.19] - 2026-09-01

### Added

- Initial production release of `bankstatementparser-loader-sepa`: ISO 20022 SEPA PAIN.002 Status & PAIN.008 Mandate Loader.
- 100% statement and branch test coverage.
- High-concurrency throughput testing (>10,000 TPS) with sub-second response times.
- Strict type hints (`mypy --strict`) and ruff linting.
- Integration with the core `bankstatementparser` ecosystem.
