# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""ISO 20022 SEPA PAIN.002 Payment Status & PAIN.008 Direct Debit Loader."""

from __future__ import annotations

from .loader import (
    SepaMessageSummary,
    SepaStatementParser,
    load_sepa,
    load_sepa_file,
    summarize_sepa,
)

__version__ = "0.0.1"
__all__ = [
    "SepaMessageSummary",
    "SepaStatementParser",
    "__version__",
    "load_sepa",
    "load_sepa_file",
    "summarize_sepa",
]
