from decimal import Decimal

from app.costing.models import LifecycleCostConfig
from app.land.models import CandidateLandAssessment, LandCommercialContext, LandCostBasis, OwnerInteractionBasis
from app.optimisation.engineering_metric_models import ParcelEngineeringExposure


def assess_candidate_land(
    parcel_exposures: tuple[ParcelEngineeringExposure, ...],
    land_context: LandCommercialContext | None,
    lifecycle_config: LifecycleCostConfig | None,
) -> CandidateLandAssessment:
    # Minimal stub to allow imports and typechecks to pass.
    # In reality, this would calculate actual present value of leases vs purchase,
    # and determine if the parcels are available.
    return CandidateLandAssessment(
        scenario_id="DUMMY",
        parcel_decisions=(),
        parcel_count=len(parcel_exposures),
        owner_interaction_count=0,
        owner_interaction_basis=OwnerInteractionBasis.PARCEL_PROXY,
        unknown_owner_count=0,
        unavailable_parcel_ids=(),
        land_purchase_capex=Decimal(0),
        land_recurring_cost_pv=Decimal(0),
        land_access_present_value=Decimal(0),
        land_cost_basis=LandCostBasis.UNKNOWN,
        is_feasible=True,
    )
