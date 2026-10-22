"""Canonical JSON and hashing shared by Python and Java (C6).

Rules, which Java must reproduce byte for byte:

* UTF-8, no BOM; object keys sorted by Unicode code point; no insignificant
  whitespace (``,`` and ``:`` separators); non-ASCII characters written as-is.
* Allowed values: objects, arrays, strings, integers, ``true``, ``false``, ``null``.
* **Floats are rejected.** Decimal quantities are written as strings such as
  ``"0.25"``, because Python and Java print doubles differently.
* The hash is lowercase hexadecimal SHA-256 of the canonical bytes.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


class CanonicalJsonError(ValueError):
    """Raised when a value cannot be represented in canonical JSON."""


def _check(value: Any, path: str) -> None:
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        raise CanonicalJsonError(
            f"{path}: floats are not canonical; write decimals as strings"
        )
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalJsonError(f"{path}: object keys must be strings")
            _check(item, f"{path}.{key}")
        return
    if isinstance(value, Sequence):
        for index, item in enumerate(value):
            _check(item, f"{path}[{index}]")
        return
    raise CanonicalJsonError(f"{path}: unsupported type {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """Serialise ``value`` to canonical JSON bytes."""
    _check(value, "$")
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Return the lowercase hex SHA-256 of ``value``'s canonical JSON."""
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
