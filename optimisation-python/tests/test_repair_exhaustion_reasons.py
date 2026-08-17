"""
Which dead end ended the repair.

``REPAIR_EXHAUSTED`` is returned from eight places in the loop, and until now the
caller got the status and an empty ``repair_log`` -- identical whether the
catalogue ran out of current, the violation was one no conductor choice can fix,
or the network was malformed. Those call for opposite responses: buy a bigger
conductor, redesign the feeder, or fix the input. The loop knows which; these
tests hold it to saying so.
"""

import networkx as nx
import pyproj
import pytest
from shapely.geometry import LineString, Point

from app.electrical.cable_sizing import CableSizingResult
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import (
    LoadFlowBusResult,
    LoadFlowNetworkResult,
    LoadFlowSegmentResult,
    LoadFlowViolation,
    LoadFlowViolationCode,
)
from app.electrical.repair import (
    RepairExhaustionReason,
    RepairStatus,
    repair_electrical_design,
)
from app.pnc.models import PNCFeeder, PNCSegment, ProjectPNCNetwork


def _network() -> ProjectPNCNetwork:
    """One feeder, one segment: SS -> W1. Enough to corner the repair loop."""
    mst = nx.Graph()
    mst.add_edges_from([("SS", "W1")])
    return ProjectPNCNetwork(
        project_id="P1",
        substation_id="SS",
        substation_geometry=Point(0, 0),
        feeders=(
            PNCFeeder(
                feeder_id="F1",
                substation_id="SS",
                wtg_ids=("W1",),
                ordered_node_ids=("SS", "W1"),
                segments=(
                    PNCSegment(
                        "S1",
                        "F1",
                        "SS",
                        "W1",
                        LineString([(0, 0), (1, 1)]),
                        1000.0,
                        1000.0,
                        "substation_to_wtg",
                    ),
                ),
                total_length_m=1000.0,
                mst_graph=mst,
            ),
        ),
        wtg_coordinates={"W1": Point(1, 1)},
        total_route_length_m=1000.0,
        feeder_count=1,
        wtg_count=1,
        segment_count=1,
        crs=pyproj.CRS.from_epsg(3857),
        route_length_by_feeder={"F1": 1000.0},
        wtg_count_by_feeder={"F1": 1},
    )


def _config(cables: tuple[LoadFlowCableType, ...]) -> LoadFlowConfig:
    return LoadFlowConfig(
        nominal_voltage_kv=33.0,
        slack_voltage_pu=1.0,
        min_voltage_pu=0.95,
        max_voltage_pu=1.05,
        system_base_mva=100.0,
        cable_types=cables,
        default_cable_type_id=cables[0].cable_type_id,
        segment_cable_type_ids={},
    )


def _invalid_result(
    violation: LoadFlowViolation,
    *,
    voltage_pu: float = 1.0,
    loading_pct: float = 80.0,
) -> LoadFlowNetworkResult:
    return LoadFlowNetworkResult(
        converged=True,
        is_valid=False,
        solver_algorithm="nr",
        total_generation_mw=10.0,
        slack_power_mw=-10.0,
        total_active_loss_mw=0.1,
        total_reactive_loss_mvar=0.1,
        minimum_voltage_pu=min(voltage_pu, 1.0),
        maximum_voltage_pu=max(voltage_pu, 1.0),
        maximum_loading_percent=loading_pct,
        buses=(
            LoadFlowBusResult("SS", "substation", 1.0, 33.0, 0.0, 0.0, 0.0),
            LoadFlowBusResult(
                "W1", "wtg", voltage_pu, 33.0 * voltage_pu, 0.0, 0.0, 0.0
            ),
        ),
        segments=(
            LoadFlowSegmentResult(
                "S1", "F1", 0, 0, 0, 0, 0, 0, loading_pct, loading_pct, 500.0, 20.0
            ),
        ),
        feeders=(),
        violations=(violation,),
    )


def _run(
    monkeypatch: pytest.MonkeyPatch,
    config: LoadFlowConfig,
    assigned_cable_id: str,
    lf_result: LoadFlowNetworkResult,
    network: ProjectPNCNetwork | None = None,
):
    monkeypatch.setattr(
        "app.electrical.repair.size_cables_for_network",
        lambda *a, **kw: CableSizingResult(
            assignments=(), segment_cable_type_ids={"S1": assigned_cable_id}
        ),
    )
    monkeypatch.setattr(
        "app.electrical.repair.run_load_flow", lambda *a, **kw: lf_result
    )
    return repair_electrical_design(
        network=network if network is not None else _network(),
        operating_points=[],
        config=config,
        wtg_active_power_mw={},
        wtg_reactive_power_mvar={},
    )


SMALL = LoadFlowCableType(
    cable_type_id="Cable-S",
    resistance_ohm_per_km=0.15,
    reactance_ohm_per_km=0.15,
    capacitance_nf_per_km=10.0,
    max_current_a=200.0,
)
# Lower impedance but more capacitance -- as every real larger conductor is.
LARGE = LoadFlowCableType(
    cable_type_id="Cable-L",
    resistance_ohm_per_km=0.05,
    reactance_ohm_per_km=0.10,
    capacitance_nf_per_km=40.0,
    max_current_a=500.0,
)

OVERVOLTAGE = LoadFlowViolation(
    LoadFlowViolationCode.BUS_OVERVOLTAGE,
    "W1 overvolt",
    node_id="W1",
    measured_value=1.06,
    limit_value=1.05,
)
OVERLOAD = LoadFlowViolation(
    LoadFlowViolationCode.CABLE_OVERLOAD,
    "S1 overloaded",
    segment_id="S1",
    measured_value=142.0,
    limit_value=100.0,
)


def test_overvoltage_exhaustion_names_the_capacitance_dead_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Voltage rise is the case where a bigger conductor is not the lever.

    The overvoltage search looks only at conductors of at least equal ampacity
    and asks for no more capacitance. Real conductors get more capacitive as they
    get larger, so it finds nothing and logs no attempt at all -- which the
    caller cannot tell from a catalogue that ran out of current.
    """
    result = _run(
        monkeypatch,
        _config((SMALL, LARGE)),
        "Cable-S",
        _invalid_result(OVERVOLTAGE, voltage_pu=1.06),
    )

    assert result.status == RepairStatus.REPAIR_EXHAUSTED
    assert result.repair_log == ()
    assert (
        result.exhaustion_reason
        == RepairExhaustionReason.NO_CONDUCTOR_REDUCES_VOLTAGE_RISE
    )


def test_overload_exhaustion_points_at_the_catalogue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The opposite finding with the opposite remedy: here a bigger conductor is
    exactly the lever and the catalogue has none left, so this must not read the
    same as a design no conductor can fix.
    """
    result = _run(
        monkeypatch,
        _config((SMALL, LARGE)),
        "Cable-L",  # already the highest-ampacity entry
        _invalid_result(OVERLOAD, loading_pct=142.0),
    )

    assert result.status == RepairStatus.REPAIR_EXHAUSTED
    assert (
        result.exhaustion_reason
        == RepairExhaustionReason.NO_LARGER_CONDUCTOR_FOR_OVERLOAD
    )


def test_undervoltage_exhaustion_is_reported_separately_from_voltage_rise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A drop and a rise are both voltage failures and want different answers."""
    result = _run(
        monkeypatch,
        _config((SMALL, LARGE)),
        "Cable-L",  # nothing larger, so nothing with lower impedance
        _invalid_result(
            LoadFlowViolation(
                LoadFlowViolationCode.BUS_UNDERVOLTAGE,
                "W1 undervolt",
                node_id="W1",
                measured_value=0.92,
                limit_value=0.95,
            ),
            voltage_pu=0.92,
        ),
    )

    assert (
        result.exhaustion_reason
        == RepairExhaustionReason.NO_CONDUCTOR_REDUCES_VOLTAGE_DROP
    )


def test_a_voltage_violation_naming_no_bus_is_an_input_problem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No bus means no path to walk, which is not a catalogue finding at all."""
    result = _run(
        monkeypatch,
        _config((SMALL, LARGE)),
        "Cable-S",
        _invalid_result(
            LoadFlowViolation(
                LoadFlowViolationCode.BUS_OVERVOLTAGE,
                "somewhere overvolt",
                node_id=None,
                measured_value=1.06,
                limit_value=1.05,
            ),
            voltage_pu=1.06,
        ),
    )

    assert result.exhaustion_reason == RepairExhaustionReason.VIOLATION_HAS_NO_BUS


def test_a_bus_in_no_feeder_is_reported_as_such(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The offending bus belongs to no feeder, so no path to it can be found."""
    result = _run(
        monkeypatch,
        _config((SMALL, LARGE)),
        "Cable-S",
        _invalid_result(
            LoadFlowViolation(
                LoadFlowViolationCode.BUS_OVERVOLTAGE,
                "stranger overvolt",
                node_id="W-not-in-this-network",
                measured_value=1.06,
                limit_value=1.05,
            ),
            voltage_pu=1.06,
        ),
    )

    assert result.exhaustion_reason == RepairExhaustionReason.BUS_NOT_IN_ANY_FEEDER


def test_sizing_failure_is_distinguished_from_an_exhausted_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repair that never began must not look like repair that tried and failed."""

    def _boom(*a: object, **kw: object) -> CableSizingResult:
        raise ValueError("no cable satisfies the sizing constraints")

    monkeypatch.setattr("app.electrical.repair.size_cables_for_network", _boom)

    result = repair_electrical_design(
        network=_network(),
        operating_points=[],
        config=_config((SMALL, LARGE)),
        wtg_active_power_mw={},
        wtg_reactive_power_mvar={},
    )

    assert result.status == RepairStatus.REPAIR_EXHAUSTED
    assert result.exhaustion_reason == RepairExhaustionReason.CABLE_SIZING_FAILED


def test_a_successful_repair_reports_no_exhaustion_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The field must mean something: set on exhaustion, absent otherwise."""
    result = _run(
        monkeypatch,
        _config((SMALL, LARGE)),
        "Cable-S",
        LoadFlowNetworkResult(
            converged=True,
            is_valid=True,
            solver_algorithm="nr",
            total_generation_mw=10.0,
            slack_power_mw=-10.0,
            total_active_loss_mw=0.1,
            total_reactive_loss_mvar=0.1,
            minimum_voltage_pu=1.0,
            maximum_voltage_pu=1.0,
            maximum_loading_percent=50.0,
            buses=(),
            segments=(),
            feeders=(),
            violations=(),
        ),
    )

    assert result.status == RepairStatus.VALID
    assert result.exhaustion_reason is None
