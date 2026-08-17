"""What the caller is told when electrical repair gives up."""

from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import (
    LoadFlowNetworkResult,
    LoadFlowViolation,
    LoadFlowViolationCode,
)
from app.electrical.repair import (
    ClosedLoopRepairResult,
    RepairAction,
    RepairExhaustionReason,
    RepairReason,
    RepairStatus,
)
from app.optimisation.candidate_evaluation import _describe_repair_failure

# The engine knew all of this and reported none of it. A run that exhausted repair
# returned
# "Electrical repair failed: REPAIR_EXHAUSTED" -- true, unactionable, and only
# debuggable by
# reading server logs on the machine that produced it.


def _config() -> LoadFlowConfig:
    return LoadFlowConfig(
        nominal_voltage_kv=33.0,
        slack_voltage_pu=1.0,
        min_voltage_pu=0.95,
        max_voltage_pu=1.05,
        system_base_mva=100.0,
        cable_types=(
            LoadFlowCableType(
                cable_type_id="Cable-S",
                resistance_ohm_per_km=0.15,
                reactance_ohm_per_km=0.15,
                capacitance_nf_per_km=0.0,
                max_current_a=200.0,
            ),
            LoadFlowCableType(
                cable_type_id="Cable-L",
                resistance_ohm_per_km=0.05,
                reactance_ohm_per_km=0.10,
                capacitance_nf_per_km=0.0,
                max_current_a=500.0,
            ),
        ),
        default_cable_type_id="Cable-S",
        segment_cable_type_ids={},
    )


def _result(
    violations: tuple[LoadFlowViolation, ...],
    repair_log: tuple[RepairAction, ...] = (),
) -> ClosedLoopRepairResult:
    return ClosedLoopRepairResult(
        status=RepairStatus.REPAIR_EXHAUSTED,
        final_electrical_config=_config(),
        load_flow_result=LoadFlowNetworkResult(
            converged=True,
            is_valid=False,
            solver_algorithm="nr",
            total_generation_mw=10.0,
            slack_power_mw=-10.0,
            total_active_loss_mw=0.1,
            total_reactive_loss_mvar=0.1,
            minimum_voltage_pu=0.912,
            maximum_voltage_pu=1.0,
            maximum_loading_percent=122.4,
            buses=(),
            segments=(),
            feeders=(),
            violations=violations,
        ),
        repair_log=repair_log,
        initial_cable_sizing=None,
    )


def _overload(segment_id: str = "SEG-FDR001-0003") -> LoadFlowViolation:
    return LoadFlowViolation(
        code=LoadFlowViolationCode.CABLE_OVERLOAD,
        message="segment overloaded",
        segment_id=segment_id,
        feeder_id="FDR-001",
        measured_value=612.0,
        limit_value=500.0,
    )


def test_names_the_segment_and_the_numbers_that_defeated_the_run() -> None:
    details = _describe_repair_failure(_result((_overload(),)), _config())

    summary = details["summary"]
    assert "SEG-FDR001-0003" in summary, "the operator needs to know where"
    assert "612" in summary and "500" in summary, "and by how much"
    assert "REPAIR_EXHAUSTED" not in summary, "a status code is not a diagnosis"


def test_reports_the_largest_conductor_it_had_to_work_with() -> None:
    # Where the biggest cable in the catalogue still is not enough, the finding is about
    # the
    # catalogue rather than the route, and saying so saves the wrong investigation.
    details = _describe_repair_failure(_result((_overload(),)), _config())

    assert details["largest_cable_available"]["cable_type_id"] == "Cable-L"
    assert details["largest_cable_available"]["effective_ampacity_a"] == 500.0
    assert details["catalogue_size"] == 2
    assert "Cable-L" in details["summary"]


def test_carries_every_unresolved_violation_with_its_limits() -> None:
    undervoltage = LoadFlowViolation(
        code=LoadFlowViolationCode.BUS_UNDERVOLTAGE,
        message="bus below limit",
        node_id="WTG-014",
        measured_value=0.912,
        limit_value=0.95,
    )
    details = _describe_repair_failure(_result((undervoltage, _overload())), _config())

    assert len(details["unresolved_violations"]) == 2
    first = details["unresolved_violations"][0]
    assert first["node_id"] == "WTG-014"
    assert first["measured_value"] == 0.912
    assert first["limit_value"] == 0.95


def test_leads_with_the_overload_rather_than_a_voltage_violation() -> None:
    # An overload has a definite fix; a voltage violation may need a different design.
    # The
    # actionable one belongs in the headline even when it is reported second.
    undervoltage = LoadFlowViolation(
        code=LoadFlowViolationCode.BUS_UNDERVOLTAGE,
        message="bus below limit",
        node_id="WTG-014",
        measured_value=0.912,
        limit_value=0.95,
    )
    details = _describe_repair_failure(_result((undervoltage, _overload())), _config())

    assert "CABLE_OVERLOAD" in details["summary"]
    assert "SEG-FDR001-0003" in details["summary"]


def test_records_every_upgrade_it_tried_before_giving_up() -> None:
    action = RepairAction(
        segment_id="SEG-FDR001-0003",
        original_cable_type_id="Cable-S",
        upgraded_cable_type_id="Cable-L",
        trigger_violation_type="CABLE_OVERLOAD",
        trigger_bus_id=None,
        pre_repair_loading_pct=140.0,
        post_repair_loading_pct=122.4,
        pre_repair_voltage_pu=None,
        post_repair_voltage_pu=None,
        repair_iteration=1,
        reason_code=RepairReason.OVERLOAD_CAPACITY_UPGRADE,
    )
    details = _describe_repair_failure(_result((_overload(),), (action,)), _config())

    assert len(details["repair_attempts"]) == 1
    attempt = details["repair_attempts"][0]
    assert attempt["from_cable_type_id"] == "Cable-S"
    assert attempt["to_cable_type_id"] == "Cable-L"
    # Loading before and after shows whether the upgrade helped at all, which is the
    # difference
    # between "no bigger cable exists" and "bigger cable does not solve this".
    assert attempt["pre_repair_loading_pct"] == 140.0
    assert attempt["post_repair_loading_pct"] == 122.4
    assert "1 conductor upgrade" in details["summary"]


def test_says_so_plainly_when_no_violation_was_reported() -> None:
    # Exhausting with an empty violation list means something else went wrong. Inventing
    # a
    # cause would be worse than admitting there isn't one.
    details = _describe_repair_failure(_result(()), _config())

    assert details["unresolved_violations"] == []
    assert "no violation reported" in details["summary"]


def test_survives_a_run_with_no_load_flow_result() -> None:
    result = ClosedLoopRepairResult(
        status=RepairStatus.REPAIR_EXHAUSTED,
        final_electrical_config=_config(),
        load_flow_result=None,
        repair_log=(),
        initial_cable_sizing=None,
    )

    details = _describe_repair_failure(result, _config())

    assert details["status"] == "REPAIR_EXHAUSTED"
    assert details["unresolved_violations"] == []


def test_reports_why_no_conductor_upgrade_was_made() -> None:
    """
    An empty ``repair_attempts`` list is not self-explanatory.

    It looks the same whether the catalogue ran out of current or the violation
    was one no conductor choice can address, and those want opposite responses.
    The loop distinguishes them; the diagnostics have to carry the distinction or
    it dies at the return statement.
    """
    result = ClosedLoopRepairResult(
        status=RepairStatus.REPAIR_EXHAUSTED,
        final_electrical_config=_config(),
        load_flow_result=None,
        repair_log=(),
        initial_cable_sizing=None,
        exhaustion_reason=RepairExhaustionReason.NO_CONDUCTOR_REDUCES_VOLTAGE_RISE,
    )

    details = _describe_repair_failure(result, _config())

    assert details["no_upgrade_reason_code"] == "NO_CONDUCTOR_REDUCES_VOLTAGE_RISE"
    reason = details["no_upgrade_reason"]
    # The sentence has to explain, not restate the code: a reader who does not
    # know the heuristic learns nothing from "NO_CONDUCTOR_REDUCES_VOLTAGE_RISE".
    assert "capacitance" in reason
    assert "NO_CONDUCTOR" not in reason


def test_distinguishes_an_exhausted_catalogue_from_an_unfixable_design() -> None:
    """The two findings point at different remedies, so they must not read alike."""
    voltage = _describe_repair_failure(
        ClosedLoopRepairResult(
            status=RepairStatus.REPAIR_EXHAUSTED,
            final_electrical_config=_config(),
            load_flow_result=None,
            repair_log=(),
            initial_cable_sizing=None,
            exhaustion_reason=(
                RepairExhaustionReason.NO_CONDUCTOR_REDUCES_VOLTAGE_RISE
            ),
        ),
        _config(),
    )["no_upgrade_reason"]
    overload = _describe_repair_failure(
        ClosedLoopRepairResult(
            status=RepairStatus.REPAIR_EXHAUSTED,
            final_electrical_config=_config(),
            load_flow_result=None,
            repair_log=(),
            initial_cable_sizing=None,
            exhaustion_reason=(RepairExhaustionReason.NO_LARGER_CONDUCTOR_FOR_OVERLOAD),
        ),
        _config(),
    )["no_upgrade_reason"]

    assert voltage != overload
    assert "catalogue" in overload


def test_says_nothing_when_there_is_no_reason_to_give() -> None:
    """A result carrying no reason must report none rather than guess one."""
    details = _describe_repair_failure(_result(()), _config())

    assert details["no_upgrade_reason_code"] is None
    assert details["no_upgrade_reason"] is None


def test_every_exhaustion_reason_has_a_sentence() -> None:
    """
    A new enum member with no entry in the table would silently surface as null,
    which is the exact failure this ticket exists to remove.
    """
    for reason in RepairExhaustionReason:
        result = ClosedLoopRepairResult(
            status=RepairStatus.REPAIR_EXHAUSTED,
            final_electrical_config=_config(),
            load_flow_result=None,
            repair_log=(),
            initial_cable_sizing=None,
            exhaustion_reason=reason,
        )
        details = _describe_repair_failure(result, _config())
        assert details["no_upgrade_reason"], f"{reason.value} has no sentence"
