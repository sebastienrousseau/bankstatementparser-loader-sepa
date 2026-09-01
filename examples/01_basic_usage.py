# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Basic usage example for bankstatementparser-loader-sepa."""

from bankstatementparser_loader_sepa import load_sepa, summarize_sepa

SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.002.001.03">
  <CstmrPmtStsRpt>
    <GrpHdr><MsgId>MSG-2026-001</MsgId></GrpHdr>
    <OrgnlGrpInfAndSts><GrpSts>ACCP</GrpSts></OrgnlGrpInfAndSts>
    <OrgnlPmtInfAndSts>
      <TxInfAndSts>
        <OrgnlEndToEndId>E2E-999</OrgnlEndToEndId>
        <TxSts>ACCP</TxSts>
        <OrgnlTxRef><Amt><InstdAmt Ccy="EUR">750.00</InstdAmt></Amt></OrgnlTxRef>
      </TxInfAndSts>
    </OrgnlPmtInfAndSts>
  </CstmrPmtStsRpt>
</Document>"""


def main() -> None:
    print("Loading statement...")
    txns = load_sepa(SAMPLE)
    for tx in txns:
        print(
            f"  Transaction: {tx.booking_date} | {tx.amount} {tx.currency} | {tx.description}"
        )

    summary = summarize_sepa(SAMPLE)
    print(f"Summary generated successfully: {summary}")


if __name__ == "__main__":
    main()
