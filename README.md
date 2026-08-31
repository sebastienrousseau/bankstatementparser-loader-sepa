# ISO 20022 SEPA PAIN.002 & PAIN.008 Loader for Bank Statement Parser

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache_2.0_OR_MIT-blue.svg)](LICENSE)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://github.com/sebastienrousseau/bankstatementparser-loader-sepa)

ISO 20022 SEPA `pain.002` (Payment Status Report) and `pain.008` (Direct Debit Initiation & Mandates) loader plugin for [`bankstatementparser`](https://github.com/sebastienrousseau/bankstatementparser).

---

## Features

- **PAIN.002 Payment Status Reports**: Ingests payment status messages (`ACTC`, `RJCT`, `PDNG`, `PART`) and extracts reject reason codes (`AC01`, `AM04`, `MS03`).
- **PAIN.008 Direct Debit & Mandates**: Ingests SEPA Direct Debit collection files and mandates (`MndtId`, sequence types, creditor/debtor details).
- **Defused XML Security**: Protection against XXE and expansion attacks.
- **Unified Domain Models**: Transforms status reports and collections into standard `Transaction` objects.

---

## Installation

```bash
pip install bankstatementparser-loader-sepa
```

---

## Quickstart

```python
from bankstatementparser_loader_sepa import load_sepa_file, summarize_sepa

# 1. Parse SEPA payment status or direct debit file
transactions = load_sepa_file("pain002_status.xml")
for tx in transactions:
    print(f"{tx.booking_date} | {tx.description} | {tx.amount} {tx.currency}")

# 2. Get message summary
summary = summarize_sepa(open("pain002_status.xml").read())
print(f"Type: {summary.message_type} | Items: {summary.item_count}")
```

---

## License

Dual-licensed under Apache 2.0 and MIT.
