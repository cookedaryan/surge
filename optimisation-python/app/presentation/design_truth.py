"""Installed design truth for the V1 response. Owned by L2 (WP1-2, WP1-5).

V0 requests still produce nothing. Profile-backed or search-backed responses
publish initial sizing provenance, final installed conductors and repair actions.
"""

from app.contracts.codes import SizingBasis
from app.contracts.resolution import ResponseContext
from app.contracts.response import (
    DesignTruth,
    InstalledSegment,
    RepairActionRecord,
)
from app.optimisation.workflow_models import OptimisationWorkflowResult
from app.presentation.exceptions import PresentationDataMismatchError


def build_design_truth(
    workflow_result: OptimisationWorkflowResult,
    context: ResponseContext,
) -> DesignTruth | None:
    if context.profile.profile_id is None and not context.search.enabled:
        return None

    recommendation = workflow_result.recommendation
    if recommendation is None or recommendation.recommended_scenario_id is None:
        return None

    candidate_id = recommendation.recommended_scenario_id
    candidate = next(
        (
            item
            for item in workflow_result.candidates
            if item.scenario.scenario_id == candidate_id
        ),
        None,
    )
    if candidate is None:
        raise PresentationDataMismatchError(
            f"Recommended candidate is missing from workflow results: {candidate_id}"
        )
    if candidate.cable_sizing is None:
        raise PresentationDataMismatchError(
            f"Recommended candidate {candidate_id} has no initial cable sizing"
        )

    network_segments = {
        segment.segment_id: (feeder.feeder_id, segment)
        for feeder in candidate.scenario.network.feeders
        for segment in feeder.segments
    }
    if len(network_segments) != candidate.scenario.network.segment_count:
        raise PresentationDataMismatchError(
            f"Recommended candidate {candidate_id} has duplicate segment IDs"
        )

    initial_conductors = dict(candidate.cable_sizing.segment_cable_type_ids)
    missing_initial = sorted(set(network_segments) - set(initial_conductors))
    extra_initial = sorted(set(initial_conductors) - set(network_segments))
    if missing_initial or extra_initial:
        raise PresentationDataMismatchError(
            "Initial cable sizing does not match recommended network segments. "
            f"Missing: {missing_initial}; extra: {extra_initial}."
        )

    final_conductors = dict(initial_conductors)
    repaired_segments: set[str] = set()
    for action in candidate.repair_log:
        current = final_conductors.get(action.segment_id)
        if current is None:
            raise PresentationDataMismatchError(
                f"Repair action references unknown segment: {action.segment_id}"
            )
        if current != action.original_cable_type_id:
            raise PresentationDataMismatchError(
                f"Repair action conductor mismatch for {action.segment_id}: "
                f"expected {current}, got {action.original_cable_type_id}"
            )
        final_conductors[action.segment_id] = action.upgraded_cable_type_id
        repaired_segments.add(action.segment_id)

    segments = [
        InstalledSegment(
            segment_id=segment_id,
            feeder_id=feeder_id,
            initial_cable_type_id=initial_conductors[segment_id],
            final_cable_type_id=final_conductors[segment_id],
            repaired=segment_id in repaired_segments,
        )
        for segment_id, (feeder_id, _segment) in sorted(
            network_segments.items(), key=lambda item: (item[1][0], item[0])
        )
    ]
    repair_actions = [
        RepairActionRecord(
            segment_id=action.segment_id,
            original_cable_type_id=action.original_cable_type_id,
            upgraded_cable_type_id=action.upgraded_cable_type_id,
            reason_code=_code_value(action.reason_code),
            trigger_violation_type=_code_value(action.trigger_violation_type),
            repair_iteration=action.repair_iteration,
        )
        for action in candidate.repair_log
    ]

    return DesignTruth(
        candidate_id=candidate_id,
        candidate_sizing_basis=SizingBasis.INITIAL_ONLY,
        segments=segments,
        repair_actions=repair_actions,
    )


def _code_value(value: object) -> str:
    enum_value = getattr(value, "value", value)
    return str(enum_value)
