# bankstatementparser-loader-sepa

**PAIN.008** (`CstmrDrctDbtInitn`) is the ISO 20022 message a creditor
sends its bank to collect SEPA Direct Debits; **PAIN.002**
(`CstmrPmtStsRpt`) is the payment status report that comes back,
settling or rejecting each transaction.

**bankstatementparser-loader-sepa** turns either message into a flat
list of
[`bankstatementparser`](https://github.com/sebastienrousseau/bankstatementparser)
`Transaction` objects (`source="sepa"`) that the rest of a
deterministic pipeline can consume unchanged.

| Concern | How this loader handles it |
| :--- | :--- |
| Message type | Detected from the `CstmrPmtStsRpt` or `CstmrDrctDbtInitn` element, or from `TxInfAndSts` / `PmtInf` content; namespaces are ignored |
| PAIN.008 | One positive transaction per `DrctDbtTxInf`, on the creditor's account, dated `ReqdColltnDt` |
| PAIN.002 | One transaction per `TxInfAndSts`; a rejected (`RJCT`) status is negative, any other keeps its sign |
| Amounts | ISO 20022 decimals to `Decimal` (never `float`); text that is not one reads as `0.00` |
| XML safety | Parsed with `defusedxml`: an entity declaration, internal or external, is refused |
| Errors | `ParseError` for text that is not XML; a `defusedxml` `ValueError` for a forbidden construct |

## In this manual

- [PAIN.002 and PAIN.008 support](format.md): the public API, the
  element mapping and the sign convention.
- [The suite](suite.md): the `bankstatementparser` packages.
- [Comparison](COMPARISON.md) and [Benchmarks](BENCHMARKS.md).
- [Supported Python policy](POLICIES.md).
- [API reference](api.md): generated from the docstrings.
- [Changelog](changelog.md) and [Security policy](security.md).

The source, issues and releases live on
[GitHub](https://github.com/sebastienrousseau/bankstatementparser-loader-sepa);
the package is on
[PyPI](https://pypi.org/project/bankstatementparser-loader-sepa/).
