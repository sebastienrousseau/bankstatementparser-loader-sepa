# Comparison

Where bankstatementparser-loader-sepa fits next to the other SEPA
packages a Python user would find on PyPI. Every cell comes from the
projects' own source code, read on 2026-11-27; nothing here is a
measured ranking.

| Project | Reads PAIN.002 | Reads PAIN.008 | Writes PAIN | XML parser | Amounts |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **bankstatementparser-loader-sepa** | Yes, any version: one signed `Transaction` per `TxInfAndSts` | Yes, any version: one `Transaction` per `DrctDbtTxInf` | No | `defusedxml` (entity declarations refused) | `Decimal`; non-ISO text reads as `0.00` |
| [`sepa`](https://github.com/VerenigingCampusKabel/python-sepa) 0.5.4 | No (listed as unsupported in its README) | `pain.008.001.07`, into nested dicts by its schema definitions | pain.008, pain.009 to pain.011 | `lxml` | Element text, unconverted |
| [`sepaxml`](https://github.com/raphaelm/python-sepaxml) 2.7.0 | No | No | pain.001 and pain.008 | None (it only builds XML) | Integer cents in, text out |
| [`bankstatementparser`](https://github.com/sebastienrousseau/bankstatementparser) 0.0.35 | No | No | No | Not applicable | Not applicable |

Evidence: `sepa/parser.py` (`parse_string` over `lxml.etree.fromstring`,
`child.text` kept as text), `sepa/messages/pain/pain008.py`
(`standard = 'pain.008.001.07'`) and the "Supported messages" list in
the `sepa` README; `sepaxml/debit.py` and `sepaxml/transfer.py` in
`sepaxml` (builders only, no parsing call); and
`bankstatementparser_loader_sepa/loader.py` here.

## When each fits

- **bankstatementparser-loader-sepa**: you want collections and their
  status reports as signed `Transaction` objects next to statements
  from other formats, to see what was settled and what was rejected.
- **`sepa`**: you need the full PAIN.008 v7 or mandate message structure
  as data, or to build those messages.
- **`sepaxml`**: you need to produce PAIN.001 or PAIN.008 files.

The wider family is listed in [The suite](suite.md).
