# Examples for bankstatementparser-loader-sepa

Runnable scripts, each with an inline SEPA sample, so no data files are
needed. CI runs every one (`tests/test_regression_examples.py` and the
`Examples` job).

- `01_basic_usage.py`: `load_sepa` and `summarize_sepa` on a PAIN.008
  collection of two Direct Debits and the PAIN.002 report that settles
  one and rejects the other.
- `02_advanced_workflow.py`: the core's `SepaStatementParser` plugin
  reading a PAIN.002 report from disk as a DataFrame and a summary, then
  listing the rejected end-to-end ids.

```sh
python examples/01_basic_usage.py
```
