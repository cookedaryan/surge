"""Structured error types for PNC network assembly failures.

A partially assembled network must never look like a successfully generated
PNC network.  All failure paths raise PNCAssemblyError with a machine-readable
error code so callers can inspect or translate the failure reason.
"""

from enum import StrEnum


class PNCAssemblyErrorCode(StrEnum):
    """Enumeration of all possible PNC assembly failure reasons."""

    FEEDER_WITHOUT_SUBSTATION_CONNECTION = "FEEDER_WITHOUT_SUBSTATION_CONNECTION"
    UNROUTED_TOPOLOGY_EDGE = "UNROUTED_TOPOLOGY_EDGE"
    ORPHAN_WTG = "ORPHAN_WTG"
    DUPLICATE_WTG_ASSIGNMENT = "DUPLICATE_WTG_ASSIGNMENT"
    UNKNOWN_FEEDER_SEGMENT = "UNKNOWN_FEEDER_SEGMENT"
    INVALID_NETWORK_CONNECTIVITY = "INVALID_NETWORK_CONNECTIVITY"
    DUPLICATE_SEGMENT_ID = "DUPLICATE_SEGMENT_ID"


class PNCAssemblyError(Exception):
    """Raised when the PNC network cannot be validly assembled.

    Attributes
    ----------
    code:
        Machine-readable reason for the failure.
    detail:
        Human-readable description with context (node IDs, feeder IDs, etc.).
    """

    def __init__(self, code: PNCAssemblyErrorCode, detail: str) -> None:
        super().__init__(f"[{code.value}] {detail}")
        self.code = code
        self.detail = detail
