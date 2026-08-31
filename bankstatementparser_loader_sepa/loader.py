# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Core ISO 20022 SEPA PAIN.002 & PAIN.008 Statement Loader."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET  # nosec B405
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import defusedxml.ElementTree as DefusedET
import pandas as pd
from bankstatementparser.base_parser import BankStatementParser
from bankstatementparser.transaction_models import Transaction

SOURCE = "sepa"


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


def _extract_account_id(acct_elem: ET.Element | None) -> str | None:
    """Extract IBAN or Other ID from an Acct node."""
    if acct_elem is None:
        return None
    iban = _find_text(acct_elem, "IBAN")
    if iban:
        return iban
    return _find_text(acct_elem, "Id")


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

    amt_elem = None
    for child in tx_node.iter():
        if (
            _clean_tag(child) in ("OrgnlTxAmt", "InstdAmt", "Amt")
            and child.text
            and child.text.strip()
        ):
            amt_elem = child
            break

    amount = Decimal("0.00")
    currency = "EUR"
    if amt_elem is not None:
        if "Ccy" in amt_elem.attrib:
            currency = amt_elem.attrib["Ccy"]
        if amt_elem.text:
            try:
                amount = Decimal(amt_elem.text.strip())
            except Exception:
                amount = Decimal("0.00")

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
    amt_elem = None
    for child in tx_node.iter():
        if (
            _clean_tag(child) == "InstdAmt"
            and child.text
            and child.text.strip()
        ):
            amt_elem = child
            break

    raw_amt = Decimal("0.00")
    curr = currency
    if amt_elem is not None:
        if "Ccy" in amt_elem.attrib:
            curr = amt_elem.attrib["Ccy"]
        if amt_elem.text:
            try:
                raw_amt = Decimal(amt_elem.text.strip())
            except Exception:
                raw_amt = Decimal("0.00")

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


def _parse_sepa_xml(
    xml_content: str | bytes,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Parse SEPA PAIN.002 or PAIN.008 XML payload."""
    if isinstance(xml_content, str):
        xml_bytes = xml_content.encode("utf-8")
    else:
        xml_bytes = xml_content

    root = DefusedET.fromstring(xml_bytes)
    root_tag = _clean_tag(root)

    # Detect PAIN.002 vs PAIN.008
    is_pain002 = False
    is_pain008 = False
    for child in root.iter():
        ctag = _clean_tag(child)
        if ctag in ("CstmrPmtStsRpt", "pain.002"):
            is_pain002 = True
            break
        if ctag in ("CstmrDrctDbtInitn", "pain.008"):
            is_pain008 = True
            break

    msg_type = (
        "PAIN.002" if is_pain002 else ("PAIN.008" if is_pain008 else root_tag)
    )
    msg_id = _find_text(root, "MsgId")
    cre_dt_tm = _find_text(root, "CreDtTm")
    creation_date = None
    if cre_dt_tm:
        try:
            clean_dt = cre_dt_tm.strip().replace("Z", "+00:00")
            creation_date = datetime.fromisoformat(clean_dt)
        except Exception:
            creation_date = None

    records: list[dict[str, Any]] = []

    if is_pain002 or (not is_pain008 and _find_text(root, "TxInfAndSts")):
        msg_type = "PAIN.002"
        for child in root.iter():
            if _clean_tag(child) == "TxInfAndSts":
                _process_pain002_tx(child, msg_id, records)

    elif is_pain008 or _find_text(root, "PmtInf"):
        msg_type = "PAIN.008"
        for pmt in root.iter():
            if _clean_tag(pmt) == "PmtInf":
                colltn_dt = _parse_iso_date(_find_text(pmt, "ReqdColltnDt"))
                cdtr_name = _find_text(pmt, "Nm")
                cdtr_acct = None
                for c in pmt.iter():
                    if _clean_tag(c) == "CdtrAcct":
                        cdtr_acct = _extract_account_id(c)
                        break
                for tx in pmt.iter():
                    if _clean_tag(tx) == "DrctDbtTxInf":
                        _process_pain008_tx(
                            tx, cdtr_name, cdtr_acct, colltn_dt, "EUR", records
                        )

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

    def get_summary(self) -> dict[str, Any]:
        """Get summary metadata and metrics for the SEPA file.

        Returns:
            Dictionary with statement statistics.
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
            "total_amount": float(s.total_amount),
        }
