# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Coverage-guided Atheris fuzz target for the SEPA PAIN.002 / PAIN.008 loader.

``load_sepa`` and ``summarize_sepa`` are the package's two entry points
for untrusted XML, and they document two failure modes:
``xml.etree.ElementTree.ParseError`` for text that is not well-formed
XML, and a ``defusedxml`` ``DefusedXmlException`` (a ``ValueError``)
for an entity declaration. Any other exception escapes
the target and libFuzzer records it as a crash, and both entry points
must refuse the same inputs.

Every transaction that loads must also be well formed: a finite amount,
``source == "sepa"`` and a ``pain002:`` or ``pain008:`` category; and
the summary of the same text must count the same transactions and total
their absolute amounts.

Run (Linux x86_64, Python 3.12+, ``poetry install --with fuzz``)::

    python fuzz/fuzz_load_sepa.py fuzz/corpus -max_total_time=60
"""

from __future__ import annotations

import sys
from decimal import Decimal
from xml.etree.ElementTree import ParseError  # nosec B405

import atheris
from defusedxml import DefusedXmlException

with atheris.instrument_imports():
    from bankstatementparser_loader_sepa import load_sepa, summarize_sepa

REFUSED = (ParseError, DefusedXmlException)


def _check_load(data: bytes) -> list[Decimal] | None:
    """Load ``data``; return the amounts, or None if it was refused."""
    try:
        transactions = load_sepa(data)
    except REFUSED:
        return None
    for txn in transactions:
        if not txn.amount.is_finite():
            raise AssertionError(f"non-finite amount {txn.amount!r}")
        category = txn.category or ""
        if txn.source != "sepa" or not category.startswith(
            ("pain002:", "pain008:")
        ):
            raise AssertionError(f"mislabelled transaction {txn!r}")
    return [txn.amount for txn in transactions]


def test_one_input(data: bytes) -> None:
    """Load and summarise one fuzz input as SEPA XML bytes."""
    amounts = _check_load(data)
    try:
        summary = summarize_sepa(data)
    except REFUSED:
        if amounts is not None:
            raise
        return
    if amounts is None:
        raise AssertionError("the summary read a message the load refused")
    if summary.item_count != len(amounts):
        raise AssertionError("summary and load disagree on the count")
    if summary.total_amount != sum((abs(a) for a in amounts), Decimal(0)):
        raise AssertionError("summary and load disagree on the total")


def main() -> None:
    """Hand the target to libFuzzer with the command-line options."""
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
