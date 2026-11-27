# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""An XML declaration naming an encoding expat cannot use is a ParseError.

``ParseError`` is the documented error for a payload that is not
readable XML. An ``encoding`` pseudo-attribute that Python does not
know (``UTF-6``), that is not a text encoding (``rot13``), that expat
refuses (multi-byte ``cp932``, ``utf-32``) or that fails to decode
(``idna``) used to escape as ``LookupError``, ``ValueError`` or
``UnicodeError`` instead. Found by fuzz/fuzz_load_sepa.py.
"""

from __future__ import annotations

from xml.etree.ElementTree import ParseError  # nosec B405

import pytest
from defusedxml import DefusedXmlException

from bankstatementparser_loader_sepa import load_sepa, summarize_sepa


@pytest.mark.parametrize(
    "encoding", ["UTF-6", "rot13", "base64", "cp932", "utf-32", "idna"]
)
def test_unusable_encoding_is_a_parse_error(encoding: str) -> None:
    """Both entry points refuse it with the documented error."""
    payload = f'<?xml version="1.0" encoding="{encoding}"?><Document/>'
    with pytest.raises(ParseError):
        load_sepa(payload)
    with pytest.raises(ParseError):
        summarize_sepa(payload.encode("ascii"))


def test_entity_refusal_is_unchanged() -> None:
    """defusedxml's refusal is still raised as itself."""
    with pytest.raises(DefusedXmlException):
        load_sepa('<!DOCTYPE x [<!ENTITY e "a">]><x>&e;</x>')


def test_a_known_single_byte_encoding_still_loads() -> None:
    """A declared Latin-1 message parses as before."""
    payload = '<?xml version="1.0" encoding="ISO-8859-1"?><Document/>'
    assert load_sepa(payload.encode("latin-1")) == []
