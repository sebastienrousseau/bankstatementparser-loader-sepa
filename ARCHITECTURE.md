<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# bankstatementparser-loader-sepa Architecture

A map of the codebase for new contributors and maintainers: how a SEPA
PAIN.002 or PAIN.008 message becomes `Transaction` objects, and where
to change what.

## The pipeline

```text
PAIN.002 / PAIN.008 payload (str, bytes, or file)
        |  defusedxml.ElementTree.fromstring (entity declarations refused)
        v
root element
        |  _collect_records: _detect_message picks the type
        |    PAIN.002 -> _collect_pain002 -> _process_pain002_tx per TxInfAndSts
        |    PAIN.008 -> _collect_pain008 -> _collect_payment_info per PmtInf
        |                                    -> _process_pain008_tx per DrctDbtTxInf
        v
header dict + list of record dicts
        |
        +--> load_sepa       -> list[Transaction] (source="sepa")
        +--> summarize_sepa  -> SepaMessageSummary (type, ids, count, total)
```

`load_sepa_file` reads a path as bytes and calls `load_sepa`, so the
XML declaration decides the encoding. `SepaStatementParser`, the plugin
the core finds through the `sepa`, `pain002` and `pain008` entry
points, wraps the same functions for the core's `parse()` (a pandas
DataFrame), `to_transactions()` and `get_summary()` (cached after the
first read).

## Modules

| Area | Module | Responsibility |
| :--- | :--- | :--- |
| **Loader** | `bankstatementparser_loader_sepa/loader.py` | XML parsing, message detection, element lookups by local name, amount and date decoding, `load_sepa` / `load_sepa_file` / `summarize_sepa`, `SepaMessageSummary`, `SepaStatementParser` |
| **Package entry** | `bankstatementparser_loader_sepa/__init__.py` | Re-exports the public API and defines `__version__` (single source of truth) |
| **Tests** | `tests/` | 100% line + branch coverage: unit tests (`test_loader.py`), characterisation of `_parse_sepa_xml` (`tests/data/`), amount validation, the golden fixtures, the README's documented behaviour (`test_docs_accuracy.py`), examples, release notes and the shared suite conformance gate |
| **Fuzzing** | `fuzz/fuzz_load_sepa.py`, `fuzz/corpus/` | Atheris target for `load_sepa` and `summarize_sepa`, run by the CI `Fuzz` job |
| **Benchmarks** | `benches/bench_load_sepa.py` | Load and summary cost as a message grows; `--quick` runs in CI |
| **Examples** | `examples/` | Two runnable scripts: a collection and its status report, and the parser plugin |
| **Manual** | `mkdocs.yml`, `docs/` | The MkDocs Material user manual and API reference, deployed to GitHub Pages |
| **Scripts** | `scripts/` | `verify_versions.py`, `release_notes.py`, `export_locked_requirements.py`, `check_complexity.py`, `check_suite_consistency.py`, `readme-check.sh` |

## Key design decisions

- **Namespace-agnostic.** Elements are matched by local name
  (`_clean_tag`), so every `pain.002.001.xx` and `pain.008.001.xx`
  version reads the same way.
- **Safe XML.** `defusedxml` refuses entity declarations, internal or
  external, before any element is read.
- **Decimal everywhere.** An amount must be ASCII digits with an
  optional fraction, as ISO 20022 defines it; anything else reads as
  `0.00`. `float` appears only in the DataFrame the core's interface
  asks for.
- **Lenient content.** Missing elements take defaults (`EUR`, status
  `RJCT`, no date) rather than raising; only XML that cannot be parsed
  or is forbidden raises.
- **Coverage enforced at 100%** line + branch and docstring, and every
  function within the suite's complexity ceilings.

## Extension points

- **Another message:** a marker in `_detect_message` and a collector
  beside `_collect_pain002` / `_collect_pain008`.
- **The sign convention:** `_process_pain002_tx`; update the README
  table and the tests with it.
- **A summary field:** extend `SepaMessageSummary`, `summarize_sepa`
  and `SepaSummaryRecord`.
