# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Read a status report through the core's parser plugin.

Installing the package registers ``SepaStatementParser`` under the
``sepa``, ``pain002`` and ``pain008`` names in the
``bankstatementparser.loaders`` entry-point group. This writes a
PAIN.002 report to disk, reads it with the plugin as a pandas DataFrame
and the summary dict, and lists the rejected end-to-end ids.
"""

import tempfile
from pathlib import Path

from bankstatementparser_loader_sepa import SepaStatementParser, load_sepa_file

REPORT = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.002.001.03">
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
    """Parse with the plugin and list the rejections."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "status.xml"
        path.write_text(REPORT, encoding="utf-8")

        parser = SepaStatementParser(str(path))
        print(parser.parse().to_string(index=False))
        print(f"\nsummary: {parser.get_summary()}")

        rejected = [
            tx.reference
            for tx in load_sepa_file(path)
            if tx.category == "pain002:RJCT"
        ]
        print(f"rejected: {', '.join(r for r in rejected if r)}")


if __name__ == "__main__":
    main()
