"""Profile definition-hash handshake endpoint (C7). Owned by L3 (WP3-6a).

Java compares this hash with its configured expected value at startup, so a
deployment whose Python and Java disagree about the profile definitions fails to
start rather than serving requests ranked under a policy Java does not know about.
FRZ-1 sets the expected value in Java configuration.

Not gated on the C5 profiles flag. The hash describes the definitions this
deployment carries, which is true whether or not profiles are currently servable,
and C7 puts the "when profiles are enabled" condition on Java's side of the
handshake. The endpoint therefore answers the same way in every deployment.
"""

from fastapi import APIRouter

from app.contracts import CONTRACT_PACK_VERSION
from app.contracts.metric_registry_version import METRIC_REGISTRY_VERSION
from app.optimisation.profiles import registry

router = APIRouter()


@router.get("/profiles/definition-hash")
def get_definition_hash() -> dict[str, str]:
    return {
        "definition_hash": registry.registry_hash(),
        "metric_registry_version": METRIC_REGISTRY_VERSION,
        "contract_pack_version": CONTRACT_PACK_VERSION,
    }
