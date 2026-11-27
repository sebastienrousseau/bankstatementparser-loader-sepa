# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Core ISO 20022 SEPA PAIN.002 & PAIN.008 Statement Loader."""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET  # nosec B405
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import defusedxml.ElementTree as DefusedET
import pandas as pd
from bankstatementparser.base_parser import BankStatementParser
from bankstatementparser.record_types import SummaryRecord
from bankstatementparser.transaction_models import Transaction
from defusedxml import DefusedXmlException

SOURCE = "sepa"

# An ISO 20022 amount (ActiveOrHistoricCurrencyAndAmount): ASCII digits
# with an optional fraction, no sign and no exponent. ``Decimal`` also
# accepts NaN, Infinity, exponents, underscores and other scripts'
# digits, none of which is an amount.
_AMOUNT = re.compile(r"[0-9]+(?:\.[0-9]+)?")


def _clean_tag(elem: ET.Element) -> str:
    """Extract the local XML tag name without namespace."""
    tag = elem.tag
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _find_text(elem: ET.Element | None, tag_name: str) -> str | None:
    """Find non-empty text of first descendant element matching local tag_name."""
    if elem is None:
        return None
    for child in elem.iter():
        if _clean_tag(child) == tag_name and child.text:
            val = child.text.strip()
            if val:
                return val
    return None


def _parse_iso_date(date_str: str | None) -> date | None:
    """Parse ISO 8601 date string."""
    if not date_str:
        return None
    clean = date_str.strip()
    if len(clean) >= 10 and clean[4] == "-" and clean[7] == "-":
        try:
            return date.fromisoformat(clean[:10])
        except ValueError:
            return None
    return None


@dataclass(frozen=True)
class SepaMessageSummary:
    """Summary metrics and headers for a SEPA PAIN.002 or PAIN.008 message."""

    message_type: str
    message_id: str | None
    creation_date: datetime | None
    account_id: str | None
    currency: str | None
    item_count: int
    total_amount: Decimal


class SepaSummaryRecord(SummaryRecord, total=False):
    """``get_summary()`` result: the core summary keys plus SEPA header fields.

    A ``SummaryRecord`` subtype, so the override matches the base parser's
    contract. ``total_amount`` is ``Decimal``, as ``SummaryRecord`` declares,
    summed from the amounts parsed out of the message text.
    """

    message_type: str
    creation_date: str | None
    item_count: int


def _extract_account_id(acct_elem: ET.Element | None) -> str | None:
    """Extract IBAN or Other ID from an Acct node."""
    if acct_elem is None:
        return None
    iban = _find_text(acct_elem, "IBAN")
    if iban:
        return iban
    return _find_text(acct_elem, "Id")


def _find_amount(
    node: ET.Element, tags: tuple[str, ...], default_currency: str
) -> tuple[Decimal, str]:
    """Return the first non-empty amount under ``node`` and its currency.

    The amount is ``0.00`` when no element named in ``tags`` has text or
    the text is not an ISO 20022 amount (ASCII digits with an optional
    fraction). The currency is the element's ``Ccy``
    attribute, or ``default_currency`` when there is none.
    """
    for child in node.iter():
        text = (child.text or "").strip()
        if _clean_tag(child) in tags and text:
            currency = child.attrib.get("Ccy", default_currency)
            if _AMOUNT.fullmatch(text):
                return Decimal(text), currency
            return Decimal("0.00"), currency
    return Decimal("0.00"), default_currency


def _process_pain002_tx(
    tx_node: ET.Element,
    msg_id: str | None,
    results: list[dict[str, Any]],
) -> None:
    """Process a single transaction status node in PAIN.002."""
    e2e_id = _find_text(tx_node, "OrgnlEndToEndId")
    tx_id = _find_text(tx_node, "OrgnlTxId") or _find_text(tx_node, "StsId")
    status = _find_text(tx_node, "TxSts") or "RJCT"
    reason_code = (
        _find_text(tx_node, "Cd") or _find_text(tx_node, "AddtlInf") or ""
    )

    amount, currency = _find_amount(
        tx_node, ("OrgnlTxAmt", "InstdAmt", "Amt"), "EUR"
    )

    # Status description
    desc = f"SEPA Status: {status}"
    if reason_code:
        desc = f"{desc} ({reason_code})"

    results.append(
        {
            "account_id": _extract_account_id(tx_node),
            "currency": currency,
            "amount": -amount if status == "RJCT" else amount,
            "booking_date": _parse_iso_date(
                _find_text(tx_node, "AccptncDtTm")
            ),
            "value_date": _parse_iso_date(_find_text(tx_node, "AccptncDtTm")),
            "description": desc,
            "reference": e2e_id or tx_id or msg_id,
            "category": f"pain002:{status}",
            "status": status,
            "reason_code": reason_code,
        }
    )


def _process_pain008_tx(
    tx_node: ET.Element,
    creditor_name: str | None,
    creditor_iban: str | None,
    colltn_dt: date | None,
    currency: str,
    results: list[dict[str, Any]],
) -> None:
    """Process a single Direct Debit transaction in PAIN.008."""
    raw_amt, curr = _find_amount(tx_node, ("InstdAmt",), currency)

    debtor_name = _find_text(tx_node, "Nm")
    debtor_iban = _extract_account_id(tx_node)
    mandate_id = _find_text(tx_node, "MndtId")
    e2e_id = _find_text(tx_node, "EndToEndId")
    rmt = _find_text(tx_node, "Ustrd") or _find_text(tx_node, "Strd") or ""

    desc = (
        f"SEPA Direct Debit - {debtor_name}"
        if debtor_name
        else "SEPA Direct Debit"
    )
    if rmt:
        desc = f"{desc} ({rmt})"

    results.append(
        {
            "account_id": creditor_iban or debtor_iban or "SEPA_DD",
            "currency": curr,
            "amount": raw_amt,
            "booking_date": colltn_dt,
            "value_date": colltn_dt,
            "description": desc,
            "reference": e2e_id or mandate_id,
            "category": "pain008:direct_debit",
            "mandate_id": mandate_id,
            "debtor_name": debtor_name,
            "creditor_name": creditor_name,
        }
    )


def _detect_message(root: ET.Element) -> tuple[bool, bool]:
    """Return ``(is_pain002, is_pain008)`` from the first marker element."""
    for child in root.iter():
        ctag = _clean_tag(child)
        if ctag in ("CstmrPmtStsRpt", "pain.002"):
            return True, False
        if ctag in ("CstmrDrctDbtInitn", "pain.008"):
            return False, True
    return False, False


def _parse_creation_date(cre_dt_tm: str | None) -> datetime | None:
    """Parse ``CreDtTm``, or return ``None`` if absent or not ISO 8601."""
    if not cre_dt_tm:
        return None
    try:
        clean_dt = cre_dt_tm.strip().replace("Z", "+00:00")
        return datetime.fromisoformat(clean_dt)
    except Exception:
        return None


def _collect_pain002(
    root: ET.Element, msg_id: str | None, records: list[dict[str, Any]]
) -> None:
    """Append a record for every ``TxInfAndSts`` node, in document order."""
    for child in root.iter():
        if _clean_tag(child) == "TxInfAndSts":
            _process_pain002_tx(child, msg_id, records)


def _creditor_account(pmt: ET.Element) -> str | None:
    """Return the account id of the first ``CdtrAcct`` under ``pmt``."""
    for c in pmt.iter():
        if _clean_tag(c) == "CdtrAcct":
            return _extract_account_id(c)
    return None


def _collect_payment_info(
    pmt: ET.Element, records: list[dict[str, Any]]
) -> None:
    """Append a record for every ``DrctDbtTxInf`` in one ``PmtInf`` block."""
    colltn_dt = _parse_iso_date(_find_text(pmt, "ReqdColltnDt"))
    cdtr_name = _find_text(pmt, "Nm")
    cdtr_acct = _creditor_account(pmt)
    for tx in pmt.iter():
        if _clean_tag(tx) == "DrctDbtTxInf":
            _process_pain008_tx(
                tx, cdtr_name, cdtr_acct, colltn_dt, "EUR", records
            )


def _collect_pain008(root: ET.Element, records: list[dict[str, Any]]) -> None:
    """Append the records of every ``PmtInf`` block, in document order."""
    for pmt in root.iter():
        if _clean_tag(pmt) == "PmtInf":
            _collect_payment_info(pmt, records)


def _collect_records(
    root: ET.Element, msg_id: str | None
) -> tuple[str, list[dict[str, Any]]]:
    """Return the message type and the records of a parsed message.

    A message with no PAIN.002 or PAIN.008 marker is still read as one
    when it has ``TxInfAndSts`` or ``PmtInf`` text; otherwise its type
    is the root element's local name and it has no records.
    """
    is_pain002, is_pain008 = _detect_message(root)
    records: list[dict[str, Any]] = []

    if is_pain002 or (not is_pain008 and _find_text(root, "TxInfAndSts")):
        _collect_pain002(root, msg_id, records)
        return "PAIN.002", records

    if is_pain008 or _find_text(root, "PmtInf"):
        _collect_pain008(root, records)
        return "PAIN.008", records

    return _clean_tag(root), records


def _parse_root(xml_bytes: bytes) -> ET.Element:
    """Parse ``xml_bytes`` with defusedxml, refusing entity declarations.

    An XML declaration naming an encoding expat cannot use raises
    ``LookupError``, ``ValueError`` or ``UnicodeError`` inside the
    parser; it is re-raised as ``ParseError``, the documented error for
    a payload that is not readable XML. defusedxml's own refusal (a
    ``ValueError`` too) is left as it is.

    Raises:
        xml.etree.ElementTree.ParseError: The payload is not readable XML.
        defusedxml.DefusedXmlException: It declares an entity.
    """
    try:
        root: ET.Element = DefusedET.fromstring(xml_bytes)
    except DefusedXmlException:
        raise
    except (LookupError, ValueError) as exc:
        raise ET.ParseError(f"unreadable XML encoding: {exc}") from exc
    return root


def _parse_sepa_xml(
    xml_content: str | bytes,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Parse SEPA PAIN.002 or PAIN.008 XML payload."""
    if isinstance(xml_content, str):
        xml_bytes = xml_content.encode("utf-8")
    else:
        xml_bytes = xml_content

    root = _parse_root(xml_bytes)
    msg_id = _find_text(root, "MsgId")
    creation_date = _parse_creation_date(_find_text(root, "CreDtTm"))
    msg_type, records = _collect_records(root, msg_id)

    header = {
        "message_type": msg_type,
        "message_id": msg_id,
        "creation_date": creation_date,
        "account_id": records[0].get("account_id") if records else None,
        "currency": records[0].get("currency", "EUR") if records else "EUR",
        "item_count": len(records),
    }

    return header, records


def load_sepa(xml_content: str | bytes) -> list[Transaction]:
    """Parse a SEPA PAIN.002 or PAIN.008 XML payload into Transaction objects.

    Args:
        xml_content: XML payload string or bytes.

    Returns:
        List of parsed Transaction instances.
    """
    _, records = _parse_sepa_xml(xml_content)
    transactions: list[Transaction] = []

    for idx, rec in enumerate(records):
        tx = Transaction(
            account_id=rec.get("account_id"),
            currency=rec.get("currency", "EUR"),
            amount=rec["amount"],
            booking_date=rec.get("booking_date"),
            value_date=rec.get("value_date"),
            description=rec.get("description"),
            reference=rec.get("reference"),
            category=rec.get("category"),
            source=SOURCE,
            source_index=idx,
        )
        transactions.append(tx)

    return transactions


def load_sepa_file(path: str | os.PathLike[str]) -> list[Transaction]:
    """Read and parse a SEPA PAIN.002 / PAIN.008 file from disk.

    Args:
        path: Path to the SEPA XML file.

    Returns:
        List of Transaction instances.
    """
    data = Path(path).read_bytes()
    return load_sepa(data)


def summarize_sepa(xml_content: str | bytes) -> SepaMessageSummary:
    """Generate financial and message summary for a SEPA document.

    Args:
        xml_content: XML payload string or bytes.

    Returns:
        A SepaMessageSummary instance.
    """
    header, records = _parse_sepa_xml(xml_content)
    total_amount = Decimal("0.00")
    for r in records:
        total_amount += abs(r["amount"])

    return SepaMessageSummary(
        message_type=header["message_type"],
        message_id=header["message_id"],
        creation_date=header["creation_date"],
        account_id=header["account_id"],
        currency=header["currency"],
        item_count=len(records),
        total_amount=total_amount,
    )


class SepaStatementParser(BankStatementParser):
    """BankStatementParser plugin implementation for SEPA PAIN.002 & PAIN.008 XML files."""

    def __init__(self, file_name: str | Path, **kwargs: Any) -> None:
        """Initialize the SEPA parser.

        Args:
            file_name: Path to the SEPA XML file.
            **kwargs: Extra options passed to base parser.
        """
        super().__init__(file_name, **kwargs)
        self._summary_cache: SepaMessageSummary | None = None

    def parse(self) -> pd.DataFrame:
        """Parse the SEPA file into a pandas DataFrame.

        Returns:
            A pandas DataFrame containing standardized statement transactions.
        """
        txs = self.to_transactions()
        if not txs:
            return pd.DataFrame(
                columns=[
                    "date",
                    "description",
                    "amount",
                    "currency",
                    "account_id",
                    "reference",
                    "source",
                ]
            )

        records = [
            {
                "date": tx.booking_date.isoformat() if tx.booking_date else "",
                "description": tx.description or "",
                "amount": float(tx.amount),
                "currency": tx.currency,
                "account_id": tx.account_id,
                "reference": tx.reference,
                "source": tx.source,
            }
            for tx in txs
        ]
        return pd.DataFrame(records)

    def to_transactions(self) -> list[Transaction]:
        """Parse the SEPA file into a list of Transaction models.

        Returns:
            List of parsed Transaction instances.
        """
        return load_sepa_file(self.file_name)

    def get_summary(self) -> SepaSummaryRecord:
        """Get summary metadata and metrics for the SEPA file.

        Returns:
            Message statistics. ``total_amount`` is ``Decimal``, as
            ``SummaryRecord`` declares.
        """
        if self._summary_cache is None:
            content = Path(self.file_name).read_bytes()
            self._summary_cache = summarize_sepa(content)

        s = self._summary_cache
        return {
            "message_type": s.message_type,
            "message_id": s.message_id,
            "creation_date": (
                s.creation_date.isoformat() if s.creation_date else None
            ),
            "account_id": s.account_id,
            "currency": s.currency,
            "item_count": s.item_count,
            "total_amount": s.total_amount,
        }
