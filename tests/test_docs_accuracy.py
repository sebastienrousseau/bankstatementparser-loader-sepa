# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""What the README says the loader does, checked against the loader.

The README's Features section is also the manual's format page
(``docs/format.md`` includes it), so these tests cover both.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path
from xml.etree.ElementTree import ParseError  # nosec B405

import pytest
from defusedxml import DefusedXmlException

from bankstatementparser_loader_sepa import load_sepa, summarize_sepa

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")


def _python_blocks() -> list[str]:
    """The fenced ``python`` blocks of the README."""
    return re.findall(r"```python\n(.*?)```", README, re.S)


def test_readme_quick_start_prints_what_it_says(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The in-memory Quick Start runs and prints its ``# `` comments."""
    (block,) = [b for b in _python_blocks() if "report = " in b]
    expected = [
        line[2:] for line in block.splitlines() if line.startswith("# ")
    ]
    exec(compile(block, "README.md", "exec"), {})
    assert capsys.readouterr().out.splitlines() == expected


def _status(body: str) -> str:
    """A PAIN.002 report with one ``TxInfAndSts`` holding ``body``."""
    return (
        "<Document><CstmrPmtStsRpt><GrpHdr><MsgId>M</MsgId></GrpHdr>"
        f"<TxInfAndSts>{body}</TxInfAndSts></CstmrPmtStsRpt></Document>"
    )


def test_a_status_without_txsts_is_a_rejection() -> None:
    """The README: "A status with no TxSts is read as RJCT"."""
    (tx,) = load_sepa(_status("<OrgnlTxAmt>5.00</OrgnlTxAmt>"))
    assert tx.category == "pain002:RJCT"
    assert tx.amount == Decimal("-5.00")


def test_the_reference_falls_back_to_the_message_id() -> None:
    """With no end-to-end, transaction or status id, ``MsgId`` is used."""
    (tx,) = load_sepa(_status("<TxSts>ACSC</TxSts>"))
    assert (tx.reference, tx.amount) == ("M", Decimal("0.00"))


def test_an_unrecognised_message_gives_no_transactions() -> None:
    """Its type is the root element's local name."""
    xml = "<Document xmlns='urn:x'><Other/></Document>"
    assert load_sepa(xml) == []
    assert summarize_sepa(xml).message_type == "Document"


@pytest.mark.parametrize(
    ("payload", "error"),
    [
        ("not xml", ParseError),
        ('<!DOCTYPE x [<!ENTITY e "a">]><x>&e;</x>', DefusedXmlException),
        (
            '<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>',
            DefusedXmlException,
        ),
    ],
)
def test_documented_errors(payload: str, error: type[Exception]) -> None:
    """The README's Errors section: the two refusals, from both calls."""
    with pytest.raises(error):
        load_sepa(payload)
    with pytest.raises(error):
        summarize_sepa(payload)
