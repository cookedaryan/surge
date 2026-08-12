"""Exceptions for the presentation boundary layer."""


class PresentationDataMismatchError(ValueError):
    """Raised when there is a mismatch between physical and electrical networks.

    Examples include missing, extra, or conflicting node IDs, segment IDs,
    feeder IDs, or node types between the PNC network and the Load Flow network.
    """

    pass
