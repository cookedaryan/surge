"""Catalogue resolution interface."""

from typing import Protocol

from app.costing.models import EngineeringCostCatalogue


class CostCatalogueProvider(Protocol):
    def get(self, catalogue_id: str) -> EngineeringCostCatalogue:
        """Resolve a cost catalogue by its identifier.

        Raises:
            CostConfigurationError: if the catalogue cannot be found or is invalid.
        """
        ...


class JSONCatalogueProvider:
    def __init__(self, catalogues: dict[str, EngineeringCostCatalogue]) -> None:
        self._catalogues = catalogues

    def get(self, catalogue_id: str) -> EngineeringCostCatalogue:
        if catalogue_id not in self._catalogues:
            from app.costing.failures import CostConfigurationError

            raise CostConfigurationError(f"Catalogue not found: {catalogue_id}")
        return self._catalogues[catalogue_id]
