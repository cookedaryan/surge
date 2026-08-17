import copy
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from pyproj import CRS

from tests.fixtures.demo_project import build_project_data

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class SyntheticProjectSpec:
    project_id: str
    turbine_count: int
    dispersion: float
    substation_offset: tuple[float, float]
    feeder_max_current_a: float
    has_constraints: bool = False
    cable_resistance_ohm_per_km: float = 0.03


PROJECT_SPECS = (
    SyntheticProjectSpec("SYN-1-CLUSTERED-8", 8, 0.005, (0.0, 0.010), 276.0),
    SyntheticProjectSpec("SYN-2-SPREAD-12", 12, 0.020, (-0.012, 0.0), 322.0),
    SyntheticProjectSpec("SYN-3-CLUSTERED-20", 20, 0.008, (0.012, 0.012), 368.0),
    SyntheticProjectSpec(
        "SYN-4-SPREAD-30",
        30,
        0.030,
        (0.0, -0.015),
        414.0,
        has_constraints=True,
        cable_resistance_ohm_per_km=0.55,
    ),
    SyntheticProjectSpec("SYN-5-MIXED-40", 40, 0.025, (0.018, 0.0), 460.0),
)


def _costing_config() -> JsonObject:
    return {
        "catalogue": {
            "catalogue_id": "CAT-SYNTHETIC-2026",
            "version": "1.0",
            "currency": "USD",
            "price_basis_date": "2026-01-01",
            "conductor_items": [
                {
                    "cable_type_id": "66kV_800mm2",
                    "installed_cost_per_km_per_parallel_circuit": 100_000.0,
                }
            ],
            "pole_items": [
                {"pole_type": "terminal", "installed_cost_each": 5_000.0},
                {"pole_type": "angle", "installed_cost_each": 6_000.0},
                {"pole_type": "intermediate", "installed_cost_each": 3_000.0},
                {"pole_type": "junction", "installed_cost_each": 7_000.0},
            ],
            "land_policy": {
                "fixed_cost_per_affected_parcel": 0.0,
                "variable_basis": "NONE",
                "variable_rate": 0.0,
            },
        },
        "lifecycle": {
            "currency": "USD",
            "energy_price_basis_date": "2026-01-01",
            "analysis_period_years": 25,
            "discount_rate": 0.08,
            "annual_operating_hours": 8_760,
            "loss_load_factor": 0.3,
            "energy_price_per_mwh": 50.0,
        },
    }


def _avoidance_geojson() -> JsonObject:
    """Return deterministic hard and soft routing constraints."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-1.004, 51.991],
                            [-0.996, 51.991],
                            [-0.996, 51.996],
                            [-1.004, 51.996],
                            [-1.004, 51.991],
                        ]
                    ],
                },
                "properties": {
                    "constraint_id": "synthetic-restricted-1",
                    "constraint_type": "RESTRICTED_AREA",
                    "routing_mode": "HARD_EXCLUSION",
                    "buffer_m": 0.0,
                },
            },
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-1.03, 52.005], [-0.97, 52.005]],
                },
                "properties": {
                    "constraint_id": "synthetic-road-1",
                    "constraint_type": "ROAD",
                    "routing_mode": "SOFT_PENALTY",
                    "buffer_m": 5.0,
                    "cost_weight": 8.0,
                },
            },
        ],
    }


def generate_synthetic_projects(
    corpus_dir: Path | None = None,
) -> tuple[Path, ...]:
    rng = random.Random(42)
    base_dir = Path(__file__).resolve().parents[3]
    fixtures_dir = base_dir / "tests" / "fixtures"
    corpus_dir = corpus_dir or fixtures_dir / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    with open(fixtures_dir / "mvp_demo_project_v2.json", encoding="utf-8") as f:
        base_json = cast(JsonObject, json.load(f))

    generated_paths = []
    for spec in PROJECT_SPECS:
        turbine_coordinates = tuple(
            (
                -1.0 + rng.uniform(-spec.dispersion, spec.dispersion),
                52.0 + rng.uniform(-spec.dispersion, spec.dispersion),
            )
            for _ in range(spec.turbine_count)
        )
        substation_coordinate = (
            -1.0 + spec.substation_offset[0],
            52.0 + spec.substation_offset[1],
        )
        project_data = build_project_data(
            turbine_coordinates,
            substation_coordinate,
            crs=CRS.from_epsg(4326),
        )

        project_json = copy.deepcopy(base_json)
        project_json["project_id"] = spec.project_id
        project_json["request_id"] = f"REQ-{spec.project_id}"
        project_json["substation_geojson"]["features"][0]["geometry"][
            "coordinates"
        ] = list(project_data.substation.location.coords[0])
        project_json["wtg_geojson"]["features"] = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": list(turbine.location.coords[0]),
                },
                "properties": {
                    "turbine_id": turbine.turbine_id,
                    "capacity_mw": turbine.capacity_mw,
                },
            }
            for turbine in project_data.turbines
        ]
        project_json["cable_config"]["cable_types"][0]["max_current_a"] = (
            spec.feeder_max_current_a
        )
        project_json["cable_config"]["cable_types"][0][
            "resistance_ohm_per_km"
        ] = spec.cable_resistance_ohm_per_km
        project_json["scenario_config"]["candidate_count"] = 2
        project_json["costing_config"] = _costing_config()
        project_json["cost_aware_config"] = {
            "engineering_weight": 0.7,
            "lifecycle_cost_weight": 0.3,
        }
        if spec.has_constraints:
            project_json["avoidance_geojson"] = _avoidance_geojson()

        output_path = corpus_dir / f"{spec.project_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(project_json, f, indent=2)
            f.write("\n")
        generated_paths.append(output_path)

    return tuple(generated_paths)


if __name__ == "__main__":
    generate_synthetic_projects()
