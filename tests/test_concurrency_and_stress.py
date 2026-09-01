# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Concurrency and stress tests for SEPA PAIN loader."""

import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from bankstatementparser_loader_sepa import load_sepa

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.002.001.03">
  <CstmrPmtStsRpt>
    <GrpHdr><MsgId>MSG-001</MsgId></GrpHdr>
    <OrgnlGrpInfAndSts><GrpSts>ACCP</GrpSts></OrgnlGrpInfAndSts>
    <OrgnlPmtInfAndSts>
      <TxInfAndSts>
        <OrgnlEndToEndId>E2E-1</OrgnlEndToEndId>
        <TxSts>ACCP</TxSts>
        <OrgnlTxRef><Amt><InstdAmt Ccy="EUR">500.00</InstdAmt></Amt></OrgnlTxRef>
      </TxInfAndSts>
    </OrgnlPmtInfAndSts>
  </CstmrPmtStsRpt>
</Document>"""


def test_sepa_concurrency() -> None:
    """Verify SEPA status parser concurrency."""
    iterations = 1000
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(load_sepa, SAMPLE_XML) for _ in range(iterations)
        ]
        results = [f.result() for f in futures]
    elapsed = time.perf_counter() - start

    assert len(results) == iterations
    for txns in results:
        assert len(txns) == 1
        assert txns[0].amount == Decimal("500.00")
    assert elapsed < 5.0
