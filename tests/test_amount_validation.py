# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""An amount is ASCII digits with an optional fraction, or it is 0.00.

ISO 20022 amounts (``ActiveOrHistoricCurrencyAndAmount``) are plain
non-negative decimals. The loader already reads text that is not a
number as ``0.00``, but ``Decimal`` accepts more than the schema does:
``NaN`` and ``Infinity`` reached ``Transaction`` and failed its
validation, ``sNaN`` escaped as ``decimal.InvalidOperation``, the
summary totalled ``NaN`` or ``Infinity``, and ``1e5``, ``1_000``, a
sign or another script's digits were read as numbers.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from bankstatementparser_loader_sepa import load_sepa, summarize_sepa


def _pain008(amount: str) -> str:
    """A one-transaction PAIN.008 with ``amount`` as its ``InstdAmt``."""
    return (
        "<Document><CstmrDrctDbtInitn><GrpHdr><MsgId>M1</MsgId></GrpHdr>"
        "<PmtInf><ReqdColltnDt>2026-01-20</ReqdColltnDt>"
        "<DrctDbtTxInf><PmtId><EndToEndId>E1</EndToEndId></PmtId>"
        f'<InstdAmt Ccy="EUR">{amount}</InstdAmt></DrctDbtTxInf>'
        "</PmtInf></CstmrDrctDbtInitn></Document>"
    )


def _pain002(amount: str) -> str:
    """A one-status PAIN.002 (rejected) with ``amount`` as its amount."""
    return (
        "<Document><CstmrPmtStsRpt><GrpHdr><MsgId>M2</MsgId></GrpHdr>"
        "<TxInfAndSts><OrgnlEndToEndId>E2</OrgnlEndToEndId>"
        "<TxSts>RJCT</TxSts>"
        f'<OrgnlTxAmt Ccy="EUR">{amount}</OrgnlTxAmt>'
        "</TxInfAndSts></CstmrPmtStsRpt></Document>"
    )


NOT_AMOUNTS = [
    "NaN",
    "sNaN",
    "Infinity",
    "-Infinity",
    "1e5",
    "1E+400",
    "1_000",
    "-5",
    "+5",
    "١٢",
    "12.",
    ".5",
]


@pytest.mark.parametrize("build", [_pain008, _pain002])
@pytest.mark.parametrize("text", NOT_AMOUNTS)
def test_text_that_is_not_an_amount_reads_as_zero(build, text: str) -> None:
    """Each message type loads and summarises a non-amount as 0.00."""
    (tx,) = load_sepa(build(text))
    assert tx.amount == Decimal("0.00")
    assert summarize_sepa(build(text)).total_amount == Decimal("0.00")


@pytest.mark.parametrize(
    ("text", "value"),
    [("12.50", Decimal("12.50")), ("7", Decimal("7")), ("0.01", None)],
)
def test_plain_decimals_still_load(text: str, value: Decimal | None) -> None:
    """Valid amounts are unchanged; a rejected status is negative."""
    expected = value if value is not None else Decimal(text)
    (debit,) = load_sepa(_pain008(text))
    (status,) = load_sepa(_pain002(text))
    assert debit.amount == expected
    assert status.amount == -expected
