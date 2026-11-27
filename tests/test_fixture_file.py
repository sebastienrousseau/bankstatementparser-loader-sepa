# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Golden tests for ``tests/fixtures/pain008.xml`` and ``pain002.xml``.

The two fixtures are one collection and its status report: a PAIN.008
batch of two Direct Debits, and the PAIN.002 that settles one and
rejects the other (reason ``AM04``). The README demo and the fuzz seeds
use them; this pins what the loader reads from each.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from bankstatementparser_loader_sepa import (
    SepaStatementParser,
    load_sepa_file,
    summarize_sepa,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_pain008_transactions() -> None:
    """Each DrctDbtTxInf is one positive collection on the creditor."""
    rows = [
        (t.booking_date, t.amount, t.account_id, t.category, t.reference)
        for t in load_sepa_file(FIXTURES / "pain008.xml")
    ]
    assert rows == [
        (
            date(2026, 1, 20),
            Decimal("64.90"),
            "DE89370400440532013000",
            "pain008:direct_debit",
            "E2E-INV-1001",
        ),
        (
            date(2026, 1, 20),
            Decimal("25.00"),
            "DE89370400440532013000",
            "pain008:direct_debit",
            "E2E-INV-1002",
        ),
    ]


def test_pain002_transactions() -> None:
    """A settled status keeps its sign; a rejection is negative."""
    rows = [
        (t.amount, t.category, t.reference, t.description)
        for t in load_sepa_file(FIXTURES / "pain002.xml")
    ]
    assert rows == [
        (
            Decimal("64.90"),
            "pain002:ACSC",
            "E2E-INV-1001",
            "SEPA Status: ACSC",
        ),
        (
            Decimal("-25.00"),
            "pain002:RJCT",
            "E2E-INV-1002",
            "SEPA Status: RJCT (AM04)",
        ),
    ]


def test_summaries() -> None:
    """Each summary names its message type and totals absolute amounts."""
    debit = summarize_sepa((FIXTURES / "pain008.xml").read_bytes())
    status = summarize_sepa((FIXTURES / "pain002.xml").read_bytes())
    assert (debit.message_type, debit.message_id) == (
        "PAIN.008",
        "DD-2026-0116",
    )
    assert (status.message_type, status.message_id) == (
        "PAIN.002",
        "STS-2026-0121",
    )
    assert debit.item_count == status.item_count == 2
    assert debit.total_amount == status.total_amount == Decimal("89.90")


def test_parser_plugin() -> None:
    """The core's plugin interface reads the same file."""
    parser = SepaStatementParser(str(FIXTURES / "pain008.xml"))
    assert list(parser.parse()["amount"]) == [64.9, 25.0]
    assert parser.get_summary()["item_count"] == 2
