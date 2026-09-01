# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Advanced batch processing example for bankstatementparser-loader-sepa."""

from decimal import Decimal

from bankstatementparser_loader_sepa import load_sepa

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
    print("Batch processing 100 iterations...")
    total_volume = Decimal("0")
    for _ in range(100):
        txns = load_sepa(SAMPLE)
        for t in txns:
            total_volume += abs(t.amount)
    print(
        f"Processed 100 batch statements. Total absolute volume: {total_volume}"
    )


if __name__ == "__main__":
    main()
