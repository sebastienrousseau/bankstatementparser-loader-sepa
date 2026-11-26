# Changelog

All notable changes to `bankstatementparser-loader-sepa` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
