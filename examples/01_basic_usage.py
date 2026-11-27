# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Load a PAIN.008 collection and the PAIN.002 report that answers it.

The collection asks for two Direct Debits; the status report settles
the first (``ACSC``) and rejects the second (``RJCT``, reason ``AM04``,
insufficient funds). The same samples are ``tests/fixtures/pain008.xml``
and ``tests/fixtures/pain002.xml``, shortened.
"""

from bankstatementparser_loader_sepa import load_sepa, summarize_sepa

COLLECTION = """<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.02">
  <CstmrDrctDbtInitn>
    <GrpHdr><MsgId>DD-2026-0116</MsgId></GrpHdr>
    <PmtInf>
      <ReqdColltnDt>2026-01-20</ReqdColltnDt>
      <Cdtr><Nm>ACME ENERGY GMBH</Nm></Cdtr>
      <CdtrAcct><Id><IBAN>DE89370400440532013000</IBAN></Id></CdtrAcct>
      <DrctDbtTxInf>
        <PmtId><EndToEndId>E2E-INV-1001</EndToEndId></PmtId>
        <InstdAmt Ccy="EUR">64.90</InstdAmt>
        <Dbtr><Nm>JANE DOE</Nm></Dbtr>
        <RmtInf><Ustrd>Electricity January</Ustrd></RmtInf>
      </DrctDbtTxInf>
      <DrctDbtTxInf>
        <PmtId><EndToEndId>E2E-INV-1002</EndToEndId></PmtId>
        <InstdAmt Ccy="EUR">25.00</InstdAmt>
        <Dbtr><Nm>JOHN SMITH</Nm></Dbtr>
        <RmtInf><Ustrd>Gas January</Ustrd></RmtInf>
      </DrctDbtTxInf>
    </PmtInf>
  </CstmrDrctDbtInitn>
</Document>"""

REPORT = """<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.002.001.03">
  <CstmrPmtStsRpt>
    <GrpHdr><MsgId>STS-2026-0121</MsgId></GrpHdr>
    <OrgnlPmtInfAndSts>
      <TxInfAndSts>
        <OrgnlEndToEndId>E2E-INV-1001</OrgnlEndToEndId>
        <TxSts>ACSC</TxSts>
        <OrgnlTxRef><Amt><InstdAmt Ccy="EUR">64.90</InstdAmt></Amt></OrgnlTxRef>
      </TxInfAndSts>
      <TxInfAndSts>
        <OrgnlEndToEndId>E2E-INV-1002</OrgnlEndToEndId>
        <TxSts>RJCT</TxSts>
        <StsRsnInf><Rsn><Cd>AM04</Cd></Rsn></StsRsnInf>
        <OrgnlTxRef><Amt><InstdAmt Ccy="EUR">25.00</InstdAmt></Amt></OrgnlTxRef>
      </TxInfAndSts>
    </OrgnlPmtInfAndSts>
  </CstmrPmtStsRpt>
</Document>"""


def main() -> None:
    """Print each message's transactions and summary."""
    for payload in (COLLECTION, REPORT):
        summary = summarize_sepa(payload)
        print(
            f"{summary.message_type} {summary.message_id}: "
            f"{summary.item_count} items, total {summary.total_amount}"
        )
        for tx in load_sepa(payload):
            print(
                f"  {tx.amount:>7} {tx.currency}  {tx.reference:<13} "
                f"{tx.category:<21} {tx.description}"
            )


if __name__ == "__main__":
    main()
