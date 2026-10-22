"""WP0B-8: cold/warm measurement harness, version 1.

Docker and the Java service are replaced by fakes that record what the harness
asked for, so the procedure itself is what these tests pin: the order of the
Compose commands, what is timed and what is not, and what a published record
may contain. The live run is an operator step; see scripts/evidence/README.md.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from scripts.evidence.baseline_reconciliation import reconcile_record
from scripts.evidence.harness import (
    CommandResult,
    ComposeStack,
    HarnessError,
    HttpResponse,
    Measurer,
    SurgeApi,
    _json_rows,
    measure,
    write_records,
)
from tests.evidence.test_baseline_reconciliation import golden, java_summary

REPO = Path(__file__).resolve().parents[3]


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@dataclass
class FakeDocker:
    clock: FakeClock
    durations: dict[str, float] = field(
        default_factory=lambda: {"pull": 30.0, "build": 90.0, "up": 20.0}
    )
    fail: str | None = None
    calls: list[list[str]] = field(default_factory=list)
    envs: list[Mapping[str, str]] = field(default_factory=list)

    def __call__(
        self, args: Sequence[str], *, cwd: Path, env: Mapping[str, str], timeout: float
    ) -> CommandResult:
        args = list(args)
        self.calls.append(args)
        self.envs.append(env)
        if args[0] == "git":
            if args[1] == "rev-parse":
                return CommandResult(0, "8ceda7f\n", "")
            return CommandResult(0, "", "")
        if args[:2] == ["docker", "info"]:
            info = {"ServerVersion": "29.8.0", "NCPU": 8, "MemTotal": 16 * 1024**3}
            return CommandResult(0, json.dumps(info), "")
        verb = next(
            a
            for a in args[2:]
            if a in {"pull", "build", "down", "up", "images", "exec"}
        )
        if verb == self.fail:
            return CommandResult(1, "", f"{verb} exploded")
        self.clock.advance(self.durations.get(verb, 0.0))
        if verb == "images":
            rows = [
                {
                    "Repository": "surge-evidence-optimizer",
                    "Tag": "latest",
                    "ID": "sha256:ab",
                }
            ]
            return CommandResult(0, json.dumps(rows), "")
        if verb == "exec":
            return CommandResult(0, "Python 3.11.9\n", "")
        return CommandResult(0, "", "")

    def verbs(self) -> list[str]:
        out = []
        for call in self.calls:
            if call[:2] == ["docker", "compose"]:
                verb = next(
                    a
                    for a in call[2:]
                    if a in {"pull", "build", "down", "up", "images", "exec"}
                )
                out.append(verb)
        return out


@dataclass
class FakeJava:
    """Just enough of the Java API: auth, project, import, jobs, layers."""

    clock: FakeClock
    summary: dict[str, Any]
    polls_before_done: int = 2
    final_status: str = "COMPLETED"
    job_seconds: float = 12.0
    requests: list[tuple[str, str, dict[str, str], bytes | None]] = field(
        default_factory=list
    )
    jobs: dict[str, int] = field(default_factory=dict)

    def __call__(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> HttpResponse:
        path = url.split("://", 1)[1].split("/", 1)[1]
        self.requests.append((method, path, dict(headers), body))
        if path == "api/v1/auth/login":
            return self._json(200, {"token": "tkn", "username": "admin"})
        if "Authorization" not in headers:
            return HttpResponse(401, b"{}")
        if path == "api/v1/projects":
            return self._json(201, {"id": "p-1"})
        if path.endswith("/assets/geojson"):
            return self._json(
                201, {"wtgsImported": 30, "substationsImported": 1, "projectId": "p-1"}
            )
        if method == "POST" and path.endswith("/jobs"):
            job_id = f"job-{len(self.jobs) + 1}"
            self.jobs[job_id] = 0
            return self._json(201, {"id": job_id, "status": "PENDING"})
        if path.endswith("/routes/geojson"):
            self.clock.advance(0.25)
            return self._json(200, {"features": [{}] * 30})
        if path.endswith("/poles/geojson"):
            self.clock.advance(0.25)
            return self._json(200, {"features": [{}] * 406})
        job_id = path.rsplit("/", 1)[1]
        self.jobs[job_id] += 1
        if self.jobs[job_id] <= self.polls_before_done:
            return self._json(200, {"id": job_id, "status": "RUNNING"})
        return self._json(
            200,
            {
                "id": job_id,
                "status": self.final_status,
                "createdAt": "2026-09-28T10:00:00Z",
                "startedAt": "2026-09-28T10:00:01Z",
                "completedAt": "2026-09-28T10:00:13.500Z",
                "errorMessage": None if self.final_status == "COMPLETED" else "boom",
                "resultSummaryJson": json.dumps(self.summary),
            },
        )

    @staticmethod
    def _json(status: int, body: object) -> HttpResponse:
        return HttpResponse(status, json.dumps(body).encode())


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def summary() -> dict[str, Any]:
    return java_summary(golden("SYN-4-SPREAD-30.golden.json"))


@pytest.fixture
def project_input(tmp_path: Path) -> Path:
    path = tmp_path / "project.geojson"
    path.write_text('{"type": "FeatureCollection", "features": []}')
    return path


def harness(
    clock: FakeClock, docker: FakeDocker, java: FakeJava
) -> tuple[ComposeStack, SurgeApi, Measurer]:
    stack = ComposeStack(
        root=REPO,
        project="surge-evidence",
        files=[REPO / "docker-compose.yml"],
        runner=docker,
        clock=clock,
    )
    api = SurgeApi("http://localhost:28080", transport=java)

    def sleep(seconds: float) -> None:
        clock.advance(seconds)

    return stack, api, Measurer(api, clock=clock, sleep=sleep, poll_interval_s=0.5)


def run_measure(
    clock: FakeClock,
    docker: FakeDocker,
    java: FakeJava,
    project_input: Path,
    **kwargs: Any,
):  # type: ignore[no-untyped-def]
    stack, api, measurer = harness(clock, docker, java)
    return measure(
        stack=stack,
        api=api,
        project_input=project_input,
        measurer=measurer,
        record_id="MSR-T",
        **{"variants": ["Balanced"], **kwargs},
    )


# --- procedure ------------------------------------------------------------------------


def test_images_are_built_once_then_every_variant_gets_a_clean_stack(
    clock: FakeClock, summary: dict[str, Any], project_input: Path
) -> None:
    docker = FakeDocker(clock)
    run_measure(
        clock,
        docker,
        FakeJava(clock, summary),
        project_input,
        variants=["Balanced", "Minimum Cost"],
    )
    assert docker.verbs() == [
        "pull",
        "build",
        "down",
        "up",
        "down",
        "up",
        "exec",
        "exec",
        "images",
        "down",
    ]
    downs = [c for c in docker.calls if "down" in c]
    assert all("-v" in c for c in downs)
    ups = [c for c in docker.calls if "up" in c]
    assert all("--no-build" in c and "--wait" in c for c in ups)


def test_build_time_is_reported_apart_from_every_run(
    clock: FakeClock, summary: dict[str, Any], project_input: Path
) -> None:
    record = run_measure(
        clock, FakeDocker(clock), FakeJava(clock, summary), project_input
    )
    assert record.stack.image_pull_build_s == 120.0
    assert record.stack.compose_up_s == [20.0]
    assert all(run.submitted_to_terminal_s < 120.0 for run in record.runs)


def test_one_cold_run_then_warm_runs_on_the_same_stack(
    clock: FakeClock, summary: dict[str, Any], project_input: Path
) -> None:
    java = FakeJava(clock, summary)
    record = run_measure(clock, FakeDocker(clock), java, project_input, warm_repeats=2)
    assert [run.kind for run in record.runs] == ["cold", "warm", "warm"]
    assert [run.job_id for run in record.runs] == ["job-1", "job-2", "job-3"]
    logins = [r for r in java.requests if r[1] == "api/v1/auth/login"]
    assert len(logins) == 1


def test_timings_come_from_submission_to_readback(
    clock: FakeClock, summary: dict[str, Any], project_input: Path
) -> None:
    (run,) = run_measure(
        clock,
        FakeDocker(clock),
        FakeJava(clock, summary),
        project_input,
        warm_repeats=0,
    ).runs
    # Two RUNNING polls at 0.5 s, then two layer reads at 0.25 s each.
    assert run.submitted_to_terminal_s == 1.0
    assert run.submitted_to_persisted_s == 1.5
    assert run.server_queue_s == 1.0
    assert run.server_run_s == 12.5
    assert (run.persisted_route_features, run.persisted_pole_features) == (30, 406)


def test_a_failed_job_is_recorded_without_reading_layers_back(
    clock: FakeClock, summary: dict[str, Any], project_input: Path
) -> None:
    java = FakeJava(clock, summary, final_status="FAILED")
    (run,) = run_measure(
        clock, FakeDocker(clock), java, project_input, warm_repeats=0
    ).runs
    assert run.job_status == "FAILED"
    assert run.submitted_to_persisted_s is None
    assert run.persisted_route_features is None
    assert run.error_message == "boom"
    assert not any(r[1].endswith("geojson") and r[0] == "GET" for r in java.requests)


def test_a_job_that_never_finishes_fails_the_measurement(
    clock: FakeClock, summary: dict[str, Any], project_input: Path
) -> None:
    java = FakeJava(clock, summary, polls_before_done=10**9)
    stack, api, measurer = harness(clock, FakeDocker(clock), java)
    measurer.job_timeout_s = 5.0
    with pytest.raises(HarnessError, match="still RUNNING"):
        measure(
            stack=stack,
            api=api,
            project_input=project_input,
            variants=["Balanced"],
            measurer=measurer,
        )


def test_a_compose_failure_stops_the_measurement_with_its_stderr(
    clock: FakeClock, summary: dict[str, Any], project_input: Path
) -> None:
    docker = FakeDocker(clock, fail="up")
    with pytest.raises(HarnessError, match="up exploded"):
        run_measure(clock, docker, FakeJava(clock, summary), project_input)


def test_an_unexpected_status_stops_the_measurement() -> None:
    def refuse(method: str, url: str, **_: Any) -> HttpResponse:
        return HttpResponse(423, b"locked out")

    api = SurgeApi("http://x", transport=refuse)  # type: ignore[arg-type]
    with pytest.raises(HarnessError, match="423: locked out"):
        api.login("admin", "pw")


# --- what a record may contain --------------------------------------------------------


def test_throwaway_secrets_reach_compose_but_never_the_record(
    clock: FakeClock, summary: dict[str, Any], project_input: Path
) -> None:
    docker = FakeDocker(clock)
    record = run_measure(clock, docker, FakeJava(clock, summary), project_input)
    compose_env = next(
        e for c, e in zip(docker.calls, docker.envs, strict=True) if "up" in c
    )
    secrets = [
        compose_env[k]
        for k in ("APP_JWT_SECRET", "DB_PASSWORD", "SURGE_BOOTSTRAP_ADMIN_PASSWORD")
    ]
    assert all(len(s) >= 24 for s in secrets)
    text = record.model_dump_json()
    assert not any(s in text for s in secrets)


def test_the_record_carries_provenance(
    clock: FakeClock, summary: dict[str, Any], project_input: Path
) -> None:
    record = run_measure(
        clock, FakeDocker(clock), FakeJava(clock, summary), project_input
    )
    assert record.revisions.revision == "8ceda7f"
    assert record.revisions.clean_worktree is True
    assert (
        "optimisation-python/requirements.lock.txt" in record.revisions.lockfile_sha256
    )
    assert record.stack.image_ids == {"surge-evidence-optimizer:latest": "sha256:ab"}
    assert record.environment.docker_cpus == 8
    assert record.environment.docker_memory_gb == 16.0
    assert record.environment.optimiser_python_version == "Python 3.11.9"
    assert record.import_counts["wtgsImported"] == 30


def test_the_blinded_copy_drops_every_result_summary(
    clock: FakeClock, summary: dict[str, Any], project_input: Path
) -> None:
    record = run_measure(
        clock, FakeDocker(clock), FakeJava(clock, summary), project_input
    )
    blinded = record.blinded_copy()
    assert blinded.blinded is True and record.blinded is False
    assert all(run.result_summary is None for run in blinded.runs)
    text = blinded.model_dump_json()
    for word in ("recommended_scenario_id", "rank", "score", "SCN-001"):
        assert word not in text


def test_raw_records_are_refused_inside_the_repository(
    clock: FakeClock, summary: dict[str, Any], project_input: Path, tmp_path: Path
) -> None:
    record = run_measure(
        clock, FakeDocker(clock), FakeJava(clock, summary), project_input
    )
    with pytest.raises(HarnessError, match="inside the repository"):
        write_records(
            record,
            raw_dir=REPO / "evidence-raw",
            published_dir=tmp_path,
            repo_root=REPO,
        )
    raw, published = write_records(
        record, raw_dir=tmp_path / "raw", published_dir=tmp_path / "pub", repo_root=REPO
    )
    assert json.loads(raw.read_text())["runs"][0]["result_summary"] is not None
    assert json.loads(published.read_text())["runs"][0]["result_summary"] is None


def test_a_raw_record_feeds_baseline_reconciliation(
    clock: FakeClock, summary: dict[str, Any], project_input: Path
) -> None:
    record = run_measure(
        clock,
        FakeDocker(clock),
        FakeJava(clock, summary),
        project_input,
        warm_repeats=1,
    )
    report = reconcile_record(record)
    assert report["violations"] == 0
    assert [run["kind"] for run in report["runs"]] == ["cold", "warm"]


def test_compose_image_listings_are_read_in_both_formats() -> None:
    rows = [{"Repository": "a", "Tag": "1", "ID": "x"}]
    assert _json_rows(json.dumps(rows)) == rows
    assert _json_rows("\n".join(json.dumps(r) for r in rows)) == rows
    assert _json_rows("") == []
