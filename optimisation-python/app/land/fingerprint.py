import hashlib
import json

from app.land.models import LandAvailabilityStatus, LandCommercialContext


def _fingerprint(state: object) -> str:
    serialized = json.dumps(state, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


def compute_land_routing_context_id(context: LandCommercialContext | None) -> str:
    """Hash the properties of land context that affect physical routing."""
    if context is None:
        return _fingerprint("LAND_ROUTING_NONE")

    # Unavailable parcels create hard exclusions, so their presence/absence
    # directly affects the valid geometry of a generated route.
    unavailable_parcels = sorted(
        p.parcel_id
        for p in context.parcel_profiles
        if p.availability_status == LandAvailabilityStatus.UNAVAILABLE
    )

    return _fingerprint({"unavailable_parcels": unavailable_parcels})


def compute_land_economic_context_id(context: LandCommercialContext | None) -> str:
    """Hash the properties of land context that affect cost and candidate ranking."""
    if context is None:
        return _fingerprint("LAND_ECONOMIC_NONE")

    profiles = []
    for p in sorted(context.parcel_profiles, key=lambda x: x.parcel_id):
        options = []
        for o in sorted(p.transaction_options, key=lambda x: x.mode.value):
            options.append(
                {
                    "mode": o.mode.value,
                    "price_status": o.price_status.value,
                    "upfront_cost": str(o.upfront_cost.normalize()),
                    "annual_cost": str(o.annual_cost.normalize()),
                    "term_years": o.term_years,
                    "price_date": o.price_date.isoformat() if o.price_date else None,
                }
            )

        profiles.append(
            {
                "parcel_id": p.parcel_id,
                "owner_id": p.owner_id,
                "availability": p.availability_status.value,
                "options": options,
            }
        )

    state = {
        "currency": context.currency,
        "as_of_date": context.as_of_date.isoformat(),
        "profiles": profiles,
    }
    return _fingerprint(state)
