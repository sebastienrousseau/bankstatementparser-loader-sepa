# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Tests for ISO 20022 SEPA PAIN.002 & PAIN.008 Statement Loader."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
from hypothesis import given
from hypothesis import strategies as st

from bankstatementparser_loader_sepa import (
    SepaMessageSummary,
    SepaStatementParser,
    __version__,
    load_sepa,
    load_sepa_file,
    summarize_sepa,
)
from bankstatementparser_loader_sepa.loader import (
    _clean_tag,
    _extract_account_id,
    _find_text,
    _parse_iso_date,
    _parse_sepa_xml,
)


def _sample_pain002_xml() -> str:
    """Return a valid ISO 20022 PAIN.002 Payment Status Report."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.002.001.10">
    <CstmrPmtStsRpt>
        <GrpHdr>
            <MsgId>MSG-STATUS-2026-001</MsgId>
            <CreDtTm>2026-01-15T14:30:00Z</CreDtTm>
        </GrpHdr>
        <OrgnlPmtInfAndSts>
            <TxInfAndSts>
                <StsId>STS-998811</StsId>
                <OrgnlEndToEndId>E2E-SALARY-01</OrgnlEndToEndId>
                <TxSts>RJCT</TxSts>
                <StsRsnInf>
                    <Rsn>
                        <Cd>AC01</Cd>
                    </Rsn>
                </StsRsnInf>
                <OrgnlTxAmt Ccy="EUR">2500.00</OrgnlTxAmt>
                <AccptncDtTm>2026-01-15T14:30:00</AccptncDtTm>
            </TxInfAndSts>
            <TxInfAndSts>
                <StsId>STS-998812</StsId>
                <OrgnlEndToEndId>E2E-SALARY-02</OrgnlEndToEndId>
                <TxSts>ACTC</TxSts>
                <OrgnlTxAmt Ccy="EUR">1800.00</OrgnlTxAmt>
                <AccptncDtTm>2026-01-15T14:30:00</AccptncDtTm>
            </TxInfAndSts>
        </OrgnlPmtInfAndSts>
    </CstmrPmtStsRpt>
</Document>
"""


def _sample_pain008_xml() -> str:
    """Return a valid ISO 20022 PAIN.008 Direct Debit Initiation."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.08">
    <CstmrDrctDbtInitn>
        <GrpHdr>
            <MsgId>MSG-DD-2026-001</MsgId>
            <CreDtTm>2026-01-16T09:00:00Z</CreDtTm>
        </GrpHdr>
        <PmtInf>
            <ReqdColltnDt>2026-01-20</ReqdColltnDt>
            <Cdtr>
                <Nm>TELECOM SERVICE CORP</Nm>
            </Cdtr>
            <CdtrAcct>
                <Id>
                    <IBAN>FR7630006000011234567890189</IBAN>
                </Id>
            </CdtrAcct>
            <DrctDbtTxInf>
                <DrctDbtTx>
                    <MndtRltdInf>
                        <MndtId>MNDT-2026-0099</MndtId>
                    </MndtRltdInf>
                </DrctDbtTx>
                <InstdAmt Ccy="EUR">89.90</InstdAmt>
                <Dbtr>
                    <Nm>ALICE JOHNSON</Nm>
                </Dbtr>
                <DbtrAcct>
                    <Id>
                        <IBAN>DE89370400440532013000</IBAN>
                    </Id>
                </DbtrAcct>
                <RmtInf>
                    <Ustrd>Fiber Internet January 2026</Ustrd>
                </RmtInf>
            </DrctDbtTxInf>
        </PmtInf>
    </CstmrDrctDbtInitn>
</Document>
"""


def test_version() -> None:
    """Verifies that version is exposed and semantic."""
    assert __version__ == "0.0.19"


def test_load_pain002_payment_status() -> None:
    """Tests loading PAIN.002 status reports."""
    xml_str = _sample_pain002_xml()
    txs = load_sepa(xml_str)

    assert len(txs) == 2

    t1 = txs[0]
    assert t1.amount == Decimal("-2500.00")
    assert t1.booking_date == date(2026, 1, 15)
    assert t1.reference == "E2E-SALARY-01"
    assert "RJCT (AC01)" in (t1.description or "")
    assert t1.category == "pain002:RJCT"
    assert t1.source == "sepa"

    t2 = txs[1]
    assert t2.amount == Decimal("1800.00")
    assert t2.reference == "E2E-SALARY-02"
    assert t2.category == "pain002:ACTC"


def test_load_pain008_direct_debit() -> None:
    """Tests loading PAIN.008 direct debit collections."""
    xml_str = _sample_pain008_xml()
    txs = load_sepa(xml_str)

    assert len(txs) == 1
    t1 = txs[0]
    assert t1.account_id == "FR7630006000011234567890189"
    assert t1.amount == Decimal("89.90")
    assert t1.currency == "EUR"
    assert t1.booking_date == date(2026, 1, 20)
    assert "ALICE JOHNSON" in (t1.description or "")
    assert "Fiber Internet" in (t1.description or "")
    assert t1.reference == "MNDT-2026-0099"
    assert t1.category == "pain008:direct_debit"


def test_summarize_sepa() -> None:
    """Tests summary extraction for PAIN.002 and PAIN.008."""
    s1 = summarize_sepa(_sample_pain002_xml())
    assert isinstance(s1, SepaMessageSummary)
    assert s1.message_type == "PAIN.002"
    assert s1.message_id == "MSG-STATUS-2026-001"
    assert s1.item_count == 2
    assert s1.total_amount == Decimal("4300.00")

    s2 = summarize_sepa(_sample_pain008_xml())
    assert s2.message_type == "PAIN.008"
    assert s2.message_id == "MSG-DD-2026-001"
    assert s2.item_count == 1
    assert s2.total_amount == Decimal("89.90")


def test_sepa_statement_parser_class(tmp_path: Path) -> None:
    """Tests SepaStatementParser BankStatementParser protocol implementation."""
    sample_file = tmp_path / "sepa.xml"
    sample_file.write_text(_sample_pain008_xml(), encoding="utf-8")

    parser = SepaStatementParser(sample_file)
    df = parser.parse()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert "amount" in df.columns
    assert "date" in df.columns
    assert "account_id" in df.columns

    summary = parser.get_summary()
    assert summary["message_type"] == "PAIN.008"
    assert summary["item_count"] == 1
    assert summary["total_amount"] == 89.90


def test_sepa_statement_parser_empty(tmp_path: Path) -> None:
    """Tests parser on empty XML."""
    empty_file = tmp_path / "empty.xml"
    empty_file.write_text(
        "<Document><Empty></Empty></Document>", encoding="utf-8"
    )

    parser = SepaStatementParser(empty_file)
    df = parser.parse()
    assert len(df) == 0
    assert "amount" in df.columns

    summary = parser.get_summary()
    assert summary["item_count"] == 0


def test_helpers_and_error_branches() -> None:
    """Tests XML helper functions and error parsing branches."""
    elem = ET.Element("{urn:test}SampleNode")
    elem.text = "Hello"
    assert _clean_tag(elem) == "SampleNode"
    assert _find_text(elem, "SampleNode") == "Hello"
    assert _find_text(None, "Any") is None
    assert _extract_account_id(None) is None

    assert _parse_iso_date("2026-01-15") == date(2026, 1, 15)
    assert _parse_iso_date("2026-99-99") is None
    assert _parse_iso_date("invalid") is None
    assert _parse_iso_date("") is None

    # Invalid amount and datetime in PAIN.002
    bad_p2 = """<Document><CstmrPmtStsRpt>
        <GrpHdr><CreDtTm>invalid-time</CreDtTm></GrpHdr>
        <TxInfAndSts><OrgnlTxAmt Ccy="USD">invalid</OrgnlTxAmt></TxInfAndSts>
    </CstmrPmtStsRpt></Document>"""
    hdr, recs = _parse_sepa_xml(bad_p2)
    assert hdr["creation_date"] is None
    assert recs[0]["amount"] == Decimal("0.00")
    assert recs[0]["currency"] == "USD"

    # Invalid amount in PAIN.008
    bad_p8 = """<Document><CstmrDrctDbtInitn>
        <PmtInf><DrctDbtTxInf><InstdAmt Ccy="GBP">bad_num</InstdAmt></DrctDbtTxInf></PmtInf>
    </CstmrDrctDbtInitn></Document>"""
    _, recs8 = _parse_sepa_xml(bad_p8)
    assert recs8[0]["amount"] == Decimal("0.00")
    assert recs8[0]["currency"] == "GBP"


def test_load_sepa_file(tmp_path: Path) -> None:
    """Tests load_sepa_file helper."""
    f = tmp_path / "test.xml"
    f.write_text(_sample_pain008_xml(), encoding="utf-8")
    txs = load_sepa_file(f)
    assert len(txs) == 1


@given(st.text(min_size=1, max_size=50))
def test_fuzz_clean_tag(tag_suffix: str) -> None:
    """Property-based fuzzing of tag cleaner."""
    elem = ET.Element(f"{{urn:iso:std:test}}{tag_suffix}")
    assert _clean_tag(elem) == tag_suffix
