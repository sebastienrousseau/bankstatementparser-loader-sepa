# Changelog

All notable changes to `bankstatementparser-loader-sepa` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Breaking:** `get_summary()` returns `total_amount` as `Decimal`, as the core
  `SummaryRecord` declares, instead of `float`. The value is exact, summed from the
  amounts parsed out of the message text. Code comparing it with a float literal
  must compare with a `Decimal` instead: `Decimal("89.90") == 89.90` is `False`.

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
