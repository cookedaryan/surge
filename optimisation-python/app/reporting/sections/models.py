from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Metric:
    name: str
    value: str | int | float | Decimal


@dataclass(frozen=True)
class Table:
    title: str
    headers: tuple[str, ...]
    rows: tuple[tuple[str | int | float | Decimal, ...], ...]


@dataclass(frozen=True)
class ReportSection:
    title: str
    summary: str | None
    metrics: tuple[Metric, ...]
    tables: tuple[Table, ...]
    notices: tuple[str, ...]
    limitations: tuple[str, ...]


def empty_section(title: str, summary: str = "Not available.") -> ReportSection:
    """Helper to construct an empty ReportSection."""
    return ReportSection(
        title=title, summary=summary, metrics=(), tables=(), notices=(), limitations=()
    )
