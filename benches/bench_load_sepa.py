#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.
"""What a SEPA PAIN.008 or PAIN.002 message costs to load, as it grows.

A PAIN.008 collection file is sized by the creditor's customer base: a
utility's monthly run carries tens of thousands of Direct Debits, split
over one ``PmtInf`` block per collection date. The PAIN.002 status
report that answers it has one ``TxInfAndSts`` per transaction. So two
messages are measured, each growing in transactions:

* **PAIN.008**: ``DrctDbtTxInf`` records spread over ``PmtInf`` blocks
  of 500.
* **PAIN.002**: ``TxInfAndSts`` records, alternately settled and
  rejected.

Read ``us/txn``. Flat means linear, and a monthly collection run is
fine. Climbing means something rescans the document for every
transaction.

``summarize_sepa`` is measured beside ``load_sepa``: it parses the same
XML but builds no ``Transaction`` objects, so the gap between the two is
what those objects cost.

Run::

    python benches/bench_load_sepa.py
    python benches/bench_load_sepa.py --json
    python benches/bench_load_sepa.py --quick     # what CI runs

Nothing here asserts a threshold: wall-clock is not comparable between
machines, and a flaky performance gate teaches people to ignore red. CI
runs ``--quick`` so a benchmark that has stopped running against the
current API fails the build instead of rotting into a file that reads
as verified and is not.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bankstatementparser_loader_sepa import (  # noqa: E402
    load_sepa,
    summarize_sepa,
)

BLOCK = 500

PAIN008_TX = (
    "<DrctDbtTxInf><PmtId><EndToEndId>E2E-{i}</EndToEndId></PmtId>"
    '<InstdAmt Ccy="EUR">{amount}</InstdAmt>'
    "<DrctDbtTx><MndtRltdInf><MndtId>MNDT-{i}</MndtId></MndtRltdInf>"
    "</DrctDbtTx><Dbtr><Nm>CUSTOMER {i}</Nm></Dbtr>"
    "<DbtrAcct><Id><IBAN>FR7630006000011234567890189</IBAN></Id>"
    "</DbtrAcct><RmtInf><Ustrd>Invoice {i}</Ustrd></RmtInf>"
    "</DrctDbtTxInf>"
)
PAIN002_TX = (
    "<TxInfAndSts><OrgnlEndToEndId>E2E-{i}</OrgnlEndToEndId>"
    "<TxSts>{status}</TxSts>{reason}"
    '<OrgnlTxRef><Amt><InstdAmt Ccy="EUR">{amount}</InstdAmt></Amt>'
    "</OrgnlTxRef></TxInfAndSts>"
)


def _amount(i: int) -> str:
    """A plain two-decimal amount that varies with ``i``."""
    return f"{(i % 9000) + 10}.{i % 100:02d}"


def build_pain008(txns: int) -> str:
    """A PAIN.008 message of ``txns`` Direct Debits, 500 per block."""
    parts = [
        "<Document><CstmrDrctDbtInitn><GrpHdr><MsgId>DD-1</MsgId>"
        "<CreDtTm>2026-01-16T09:00:00Z</CreDtTm></GrpHdr>"
    ]
    for start in range(0, txns, BLOCK):
        parts.append(
            "<PmtInf><ReqdColltnDt>2026-01-20</ReqdColltnDt>"
            "<Cdtr><Nm>ACME ENERGY GMBH</Nm></Cdtr><CdtrAcct><Id>"
            "<IBAN>DE89370400440532013000</IBAN></Id></CdtrAcct>"
        )
        for i in range(start, min(start + BLOCK, txns)):
            parts.append(PAIN008_TX.format(i=i, amount=_amount(i)))
        parts.append("</PmtInf>")
    parts.append("</CstmrDrctDbtInitn></Document>")
    return "".join(parts)


def build_pain002(txns: int) -> str:
    """A PAIN.002 report of ``txns`` statuses, alternately ACSC and RJCT."""
    parts = [
        "<Document><CstmrPmtStsRpt><GrpHdr><MsgId>STS-1</MsgId>"
        "<CreDtTm>2026-01-21T08:15:00Z</CreDtTm></GrpHdr>"
        "<OrgnlPmtInfAndSts>"
    ]
    for i in range(txns):
        rejected = i % 2
        parts.append(
            PAIN002_TX.format(
                i=i,
                status="RJCT" if rejected else "ACSC",
                reason=(
                    "<StsRsnInf><Rsn><Cd>AM04</Cd></Rsn></StsRsnInf>"
                    if rejected
                    else ""
                ),
                amount=_amount(i),
            )
        )
    parts.append("</OrgnlPmtInfAndSts></CstmrPmtStsRpt></Document>")
    return "".join(parts)


BUILDERS: dict[str, Callable[[int], str]] = {
    "PAIN.008": build_pain008,
    "PAIN.002": build_pain002,
}


def _best(call: Callable[[], object], repeats: int) -> float:
    """Best-of timing after one untimed warm-up.

    The minimum is the least noisy estimator available; the mean follows
    whatever else the machine happens to be doing.
    """
    call()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        call()
        samples.append(time.perf_counter() - start)
    return min(samples)


def measure(message: str, txns: int, repeats: int) -> dict[str, Any]:
    """Time ``load_sepa`` and ``summarize_sepa`` on one message size."""
    text = BUILDERS[message](txns)
    load = _best(lambda: load_sepa(text), repeats)
    summary = _best(lambda: summarize_sepa(text), repeats)
    loaded = len(load_sepa(text))
    summarised = summarize_sepa(text)
    if loaded != txns or summarised.item_count != txns:
        raise SystemExit(f"expected {txns} transactions, read {loaded}")
    if summarised.message_type != message:
        raise SystemExit(f"read {summarised.message_type}, not {message}")
    return {
        "message": message,
        "transactions": loaded,
        "bytes": len(text),
        "load_ms": load * 1e3,
        "summary_ms": summary * 1e3,
        "us_per_txn": load * 1e6 / loaded,
        "summary_over_load": summary / load,
    }


def run(quick: bool) -> list[dict[str, Any]]:
    """Measure every message and size; ``quick`` keeps to the small ones."""
    if quick:
        sizes, repeats = [10, 100], 3
    else:
        sizes, repeats = [10, 100, 1_000, 10_000, 50_000], 5
    return [measure(m, n, repeats) for m in BUILDERS for n in sizes]


def render(rows: list[dict[str, Any]]) -> None:
    """Print the table and what it means."""
    print(
        f"{'message':>9}{'txns':>8}{'KiB':>10}{'load ms':>11}"
        f"{'summary ms':>12}{'us/txn':>9}"
    )
    for row in rows:
        print(
            f"{row['message']:>9}{row['transactions']:>8}"
            f"{row['bytes'] / 1024:>10.1f}{row['load_ms']:>11.2f}"
            f"{row['summary_ms']:>12.2f}{row['us_per_txn']:>9.2f}"
        )
    for message in BUILDERS:
        mine = [r for r in rows if r["message"] == message]
        drift = mine[-1]["us_per_txn"] / mine[0]["us_per_txn"]
        print(
            f"\n  {message}: us/txn at {mine[-1]['transactions']:,} is "
            f"{drift:.2f}x the cost at {mine[0]['transactions']:,}. Flat "
            f"is linear; climbing means a rescan per transaction."
        )
    worst = max(r["summary_over_load"] for r in rows)
    print(
        f"\n  summarize_sepa costs up to {worst:.2f}x load_sepa. Both "
        f"parse the whole document; the summary saves only building the "
        f"Transaction objects."
    )


def main() -> int:
    """Parse the options, run, and print a table or JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--quick", action="store_true", help="small sizes, as CI runs"
    )
    args = parser.parse_args()

    rows = run(quick=args.quick)
    if args.json:
        json.dump(rows, sys.stdout, indent=1)
        print()
    else:
        render(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
