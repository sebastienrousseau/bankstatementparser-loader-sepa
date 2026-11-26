# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Characterisation tests for ``_parse_sepa_xml``.

They pin the exact header and records each message produces today:
how the message type is detected (root elements, the ``pain.002`` and
``pain.008`` tags, the ``TxInfAndSts`` and ``PmtInf`` fallbacks),
creation-date parsing, the creditor-account lookup and the order in
which records are collected. The expected values in
``data/parse_sepa_xml.json`` are what the code returned when the tests
were written, not a specification. Regenerate them only for a change
that is meant to alter behaviour.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET  # nosec B405
from pathlib import Path

import pytest

from bankstatementparser_loader_sepa.loader import _parse_sepa_xml

_EXPECTED_PATH = Path(__file__).parent / "data" / "parse_sepa_xml.json"

_P002_TX = (
    "<TxInfAndSts><StsId>S1</StsId><OrgnlEndToEndId>E1</OrgnlEndToEndId>"
    "<TxSts>RJCT</TxSts><Cd>AC01</Cd>"
    '<OrgnlTxAmt Ccy="EUR">25.00</OrgnlTxAmt>'
    "<AccptncDtTm>2026-01-15T14:30:00</AccptncDtTm></TxInfAndSts>"
    "<TxInfAndSts><OrgnlTxId>T2</OrgnlTxId><TxSts>ACTC</TxSts>"
    "<AddtlInf>ok</AddtlInf><InstdAmt>7</InstdAmt>"
    "<IBAN>DE89370400440532013000</IBAN></TxInfAndSts>"
)
_DD_TX = (
    "<DrctDbtTxInf><MndtId>M1</MndtId><EndToEndId>E8</EndToEndId>"
    '<InstdAmt Ccy="EUR">89.90</InstdAmt><Dbtr><Nm>ALICE</Nm></Dbtr>'
    "<DbtrAcct><Id><IBAN>DE89</IBAN></Id></DbtrAcct>"
    "<Ustrd>Fiber</Ustrd></DrctDbtTxInf>"
)
_PMT = (
    "<PmtInf><ReqdColltnDt>2026-01-20</ReqdColltnDt>"
    "<Cdtr><Nm>TELECOM</Nm></Cdtr>"
    "<CdtrAcct><Id><IBAN>FR76</IBAN></Id></CdtrAcct>"
    "<CdtrAcct><Id><IBAN>FR99</IBAN></Id></CdtrAcct>"
    f"{_DD_TX}{_DD_TX.replace('M1', 'M2')}</PmtInf>"
    "<PmtInf><Cdtr><Nm>NO ACCOUNT</Nm></Cdtr>"
    "<CdtrAcct><Id><Othr><Id>ACC-1</Id></Othr></Id></CdtrAcct>"
    '<DrctDbtTxInf><InstdAmt Ccy="GBP">1</InstdAmt></DrctDbtTxInf>'
    "</PmtInf>"
    "<PmtInf><DrctDbtTxInf><InstdAmt>2</InstdAmt></DrctDbtTxInf></PmtInf>"
)
_HDR = (
    "<GrpHdr><MsgId>MSG-1</MsgId>"
    "<CreDtTm>2026-01-15T14:30:00Z</CreDtTm></GrpHdr>"
)
_NS = "urn:iso:std:iso:20022:tech:xsd"

_CASES: dict[str, str | bytes] = {
    "pain002_root": (
        f'<Document xmlns="{_NS}:pain.002.001.10"><CstmrPmtStsRpt>'
        f"{_HDR}{_P002_TX}</CstmrPmtStsRpt></Document>"
    ),
    "pain002_bytes": (
        f"<Document><CstmrPmtStsRpt>{_HDR}{_P002_TX}"
        "</CstmrPmtStsRpt></Document>"
    ).encode(),
    "pain002_tag": f"<pain.002>{_P002_TX}</pain.002>",
    "pain002_no_tx": "<Document><CstmrPmtStsRpt/></Document>",
    "pain008_root": (
        f'<Document xmlns="{_NS}:pain.008.001.08"><CstmrDrctDbtInitn>'
        f"{_HDR}{_PMT}</CstmrDrctDbtInitn></Document>"
    ),
    "pain008_tag": f"<pain.008>{_PMT}</pain.008>",
    "pain008_no_tx": "<Document><CstmrDrctDbtInitn/></Document>",
    "pain008_wins_when_first": (
        f"<Doc><CstmrDrctDbtInitn/><CstmrPmtStsRpt/>"
        f"<TxInfAndSts>t</TxInfAndSts>{_PMT}</Doc>"
    ),
    "pain002_wins_when_first": (
        f"<Doc><CstmrPmtStsRpt/><CstmrDrctDbtInitn/>{_P002_TX}{_PMT}</Doc>"
    ),
    "fallback_tx_with_text": (
        f"<Doc><TxInfAndSts>x<TxSts>ACCP</TxSts></TxInfAndSts>{_PMT}</Doc>"
    ),
    "fallback_tx_without_text": (
        f"<Doc><TxInfAndSts><TxSts>ACCP</TxSts></TxInfAndSts>{_PMT}</Doc>"
    ),
    "fallback_pmtinf_with_text": (
        f"<Doc><PmtInf>p{_DD_TX}</PmtInf>{_HDR}</Doc>"
    ),
    "nested_pmtinf": (
        f"<Doc><CstmrDrctDbtInitn><PmtInf><Nm>OUTER</Nm>"
        f"<PmtInf><Nm>INNER</Nm>{_DD_TX}</PmtInf></PmtInf>"
        "</CstmrDrctDbtInitn></Doc>"
    ),
    "nested_txinfandsts": (
        "<Doc><CstmrPmtStsRpt><TxInfAndSts><TxSts>A</TxSts>"
        "<TxInfAndSts><TxSts>B</TxSts></TxInfAndSts></TxInfAndSts>"
        "</CstmrPmtStsRpt></Doc>"
    ),
    "msg_id_reference_and_currency": (
        "<Doc><CstmrPmtStsRpt><MsgId>M-9</MsgId><TxInfAndSts>"
        '<TxSts>ACCP</TxSts><Amt Ccy="USD">3</Amt></TxInfAndSts>'
        "</CstmrPmtStsRpt></Doc>"
    ),
    "non_ascii_str": (
        "<Doc><CstmrDrctDbtInitn><PmtInf><Nm>Société Générale</Nm>"
        f"{_DD_TX.replace('ALICE', 'Jürgen Müller')}</PmtInf>"
        "</CstmrDrctDbtInitn></Doc>"
    ),
    "unknown": f'<Other xmlns="{_NS}:camt.053"><TxSts>X</TxSts></Other>',
    "empty": "<Empty/>",
    "credttm_offset": (
        "<Doc><CstmrPmtStsRpt><CreDtTm>2026-01-15T14:30:00+02:00</CreDtTm>"
        "</CstmrPmtStsRpt></Doc>"
    ),
    "credttm_naive": (
        "<Doc><CstmrPmtStsRpt><CreDtTm> 2026-01-15T14:30:00 </CreDtTm>"
        "</CstmrPmtStsRpt></Doc>"
    ),
    "credttm_date_only": (
        "<Doc><CstmrPmtStsRpt><CreDtTm>2026-01-15</CreDtTm>"
        "</CstmrPmtStsRpt></Doc>"
    ),
    "credttm_invalid": (
        "<Doc><CstmrPmtStsRpt><CreDtTm>not-a-time</CreDtTm>"
        "</CstmrPmtStsRpt></Doc>"
    ),
    "credttm_blank": (
        "<Doc><CstmrPmtStsRpt><CreDtTm>  </CreDtTm>"
        "<MsgId>  </MsgId></CstmrPmtStsRpt></Doc>"
    ),
}


def _expected() -> dict[str, str]:
    """Load the pinned ``repr`` of each case's result."""
    data: dict[str, str] = json.loads(_EXPECTED_PATH.read_text("utf-8"))
    return data


def test_every_case_is_pinned() -> None:
    """The cases and the pinned results name the same messages."""
    assert sorted(_expected()) == sorted(_CASES)


@pytest.mark.parametrize("name", sorted(_CASES))
def test_parse_sepa_xml_result_is_unchanged(name: str) -> None:
    """Each message yields exactly the header and records pinned for it."""
    # repr, not ==, so key order, a Decimal's exponent, a timezone and
    # a value's type count too.
    assert repr(_parse_sepa_xml(_CASES[name])) == _expected()[name]


def test_malformed_xml_still_raises() -> None:
    """A payload that is not XML is not swallowed."""
    with pytest.raises(ET.ParseError, match="no element found"):
        _parse_sepa_xml("<Doc>")
