import csv
import json
import logging
import sys
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

COMPONENT_DIR = Path(__file__).resolve().parent.parent
if str(COMPONENT_DIR) not in sys.path:
    sys.path.insert(0, str(COMPONENT_DIR))

from app.optimisation.orchestrator import optimise_project
from app.optimisation.workflow_models import OptimisationStatus
from app.schemas.v2.domain_mapping import to_workflow_invocation
from app.schemas.v2.optimise import OptimiseProjectRequest

logging.basicConfig(level=logging.INFO)


REQUIRED_LABELS = (
    "evaluation.rank",
    "feasible",
    "evaluation.lifecycle_cost",
    "total_route_length_m",
)


def _validate_corpus(output_path: Path, expected_projects: set[str]) -> None:
    with open(output_path, newline="", encoding="utf-8") as corpus_file:
        rows = list(csv.DictReader(corpus_file))

    if not rows:
        raise RuntimeError("Corpus generation produced no training rows")

    actual_projects = {row["project_id"] for row in rows}
    if actual_projects != expected_projects:
        raise RuntimeError(
            "Corpus project coverage mismatch: "
            f"expected {sorted(expected_projects)}, got {sorted(actual_projects)}"
        )

    missing_columns = set(REQUIRED_LABELS).difference(rows[0])
    if missing_columns:
        raise RuntimeError(
            f"Corpus is missing required label columns: {sorted(missing_columns)}"
        )

    incomplete_rows = []
    for row in rows:
        if not row["feasible"].strip() or not row["total_route_length_m"].strip():
            incomplete_rows.append(row["scenario_id"])
            continue
        if row["feasible"] == "True" and (
            not row["evaluation.rank"].strip()
            or not row["evaluation.lifecycle_cost"].strip()
        ):
            incomplete_rows.append(row["scenario_id"])
    if incomplete_rows:
        raise RuntimeError(
            "Corpus contains rows with missing labels: "
            + ", ".join(incomplete_rows[:10])
        )


def generate_corpus(output_path: Path | None = None) -> Path:
    fixtures_dir = COMPONENT_DIR / "tests" / "fixtures" / "corpus"
    output_path = output_path or COMPONENT_DIR / "search_corpus.csv"

    expected_projects = set()
    writer: csv.DictWriter | None = None
    with open(output_path, "w", newline="", encoding="utf-8") as corpus_file:

        def corpus_sink(row: Mapping[str, object]) -> None:
            nonlocal writer
            if writer is None:
                writer = csv.DictWriter(corpus_file, fieldnames=list(row))
                writer.writeheader()
            writer.writerow(row)

        for json_file in sorted(fixtures_dir.glob("SYN-*.json")):
            logging.info("Processing %s...", json_file.name)
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)

            req = OptimiseProjectRequest.model_validate(data)
            inv = to_workflow_invocation(req)
            expected_projects.add(inv.project_input.project_id)

            new_search_config = replace(
                inv.config.search,
                enabled=True,
                emit_training_corpus=True,
                corpus_neighbor_override=50,
            )
            new_config = replace(inv.config, search=new_search_config)

            res = optimise_project(
                inv.project_input,
                new_config,
                corpus_sink=corpus_sink,
            )
            if res.status not in {
                OptimisationStatus.SUCCESS,
                OptimisationStatus.PARTIAL_SUCCESS,
            }:
                raise RuntimeError(
                    f"{json_file.name} failed with status {res.status.value}"
                )

            logging.info(
                "Finished %s with status %s", json_file.name, res.status.value
            )

    _validate_corpus(output_path, expected_projects)
    return output_path


if __name__ == "__main__":
    generate_corpus()
