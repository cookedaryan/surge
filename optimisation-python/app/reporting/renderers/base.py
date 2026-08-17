from abc import ABC, abstractmethod

from app.reporting.report import EngineeringReport


class ReportRenderer(ABC):
    @abstractmethod
    def render(self, report: EngineeringReport) -> str:
        """Render an EngineeringReport to a string format."""
        pass
