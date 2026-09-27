"""Cold/warm measurement harness. Owned by L2 (WP0B-8).

Measures one project through the real stack: a Compose deployment, a Java job
submission, and the persisted result read back over the Java API. Every
measurement is taken from outside the stack, the way an operator sees it.

Procedure, harness version 1
----------------------------
* **Images are built first and timed on their own.** ``pull`` and ``build``
  are reported as ``image_pull_build_s`` and never counted in a run.
* **Cold** means a clean Compose start: ``down -v`` removes the containers and
  the database volume, then ``up --wait`` starts the prebuilt images. Every
  application cache starts empty, because none of them survives a container.
  The first submission after that start is the cold run.
* **Warm** means another submission of the same variant on the same running
  stack, after a cold run. Nothing is restarted between them.
* **Submitted to persisted** is measured from the job ``POST`` until the job
  reports a terminal status *and* its routes and poles can be read back. Java
  announces completion only after commit, but "announced" is not "readable",
  so the harness checks both. The poll interval bounds its resolution and is
  recorded.
* **Blinding.** A raw record keeps each job's full result summary, which
  carries ranks, scores and the recommendation. It is written only outside the
  repository, and ``blinded()`` removes every summary before anything is
  published. Reconciliation (WP0B-9) reads the raw record and publishes
  equation results only.

Secrets for the stack are generated per run and never written to a record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import secrets
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

HARNESS_VERSION: Final = "1"
COLD_DEFINITION = (
    "Compose down -v (containers and database volume removed), then up --wait "
    "on prebuilt images; application caches empty; image pull/build timed "
    "separately"
)
TERMINAL_STATUSES = frozenset({"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"})
LOCKFILES = (
    "optimisation-python/requirements.lock.txt",
    "web-map-next/package-lock.json",
    "backend-java/pom.xml",
)

RunKind = Literal["cold", "warm"]
REQUEST_VARIANTS = (
    "Balanced",
    "Minimum Cost",
    "Minimum Land Impact",
    "Minimum Environmental Impact",
)


# --- records --------------------------------------------------------------------------


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class StackTimings(_Record):
    image_pull_build_s: float | None = Field(default=None, ge=0)
    compose_up_s: list[float]
    image_ids: dict[str, str]


class Revisions(_Record):
    revision: str
    clean_worktree: bool
    lockfile_sha256: dict[str, str]


class Environment(_Record):
    host_os: str
    docker_server_version: str | None
    docker_cpus: int | None
    docker_memory_gb: float | None
    optimiser_python_version: str | None
    backend_java_version: str | None
    cold_definition: str


class RunMeasurement(_Record):
    request_variant: str
    kind: RunKind
    job_id: str
    job_status: str
    submitted_to_terminal_s: float = Field(ge=0)
    submitted_to_persisted_s: float | None = Field(default=None, ge=0)
    server_queue_s: float | None = Field(default=None, ge=0)
    server_run_s: float | None = Field(default=None, ge=0)
    persisted_route_features: int | None = Field(default=None, ge=0)
    persisted_pole_features: int | None = Field(default=None, ge=0)
    error_message: str | None = None
    # Access-controlled: ranks, scores and the recommendation. Never published.
    result_summary: dict[str, Any] | None = None


class MeasurementRecord(_Record):
    harness_version: Literal["1"] = HARNESS_VERSION
    record_id: str
    created_at: str
    blinded: bool
    project_input_sha256: str
    import_counts: dict[str, int]
    revisions: Revisions
    environment: Environment
    stack: StackTimings
    poll_interval_s: float = Field(gt=0)
    runs: list[RunMeasurement]

    def blinded_copy(self) -> MeasurementRecord:
        """Return the publishable form: no result summaries, marked blinded."""
        runs = [run.model_copy(update={"result_summary": None}) for run in self.runs]
        return self.model_copy(update={"blinded": True, "runs": runs})


# --- process and HTTP seams -----------------------------------------------------------


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    def __call__(
        self, args: Sequence[str], *, cwd: Path, env: Mapping[str, str], timeout: float
    ) -> CommandResult: ...


def run_command(
    args: Sequence[str], *, cwd: Path, env: Mapping[str, str], timeout: float
) -> CommandResult:
    completed = subprocess.run(  # noqa: S603 - arguments are built by this module
        list(args),
        cwd=cwd,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body)


class HttpTransport(Protocol):
    def __call__(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> HttpResponse: ...


def urllib_transport(
    method: str,
    url: str,
    *,
    headers: Mapping[str, str],
    body: bytes | None,
    timeout: float,
) -> HttpResponse:
    request = urllib.request.Request(
        url, data=body, method=method, headers=dict(headers)
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return HttpResponse(response.status, response.read())
    except urllib.error.HTTPError as error:
        return HttpResponse(error.code, error.read())


class HarnessError(RuntimeError):
    """A measurement could not be taken; nothing partial is recorded."""


# --- Compose stack --------------------------------------------------------------------


@dataclass
class ComposeStack:
    """One isolated Compose project built from a checkout of the repository."""

    root: Path
    project: str
    files: Sequence[Path]
    runner: CommandRunner = run_command
    clock: Callable[[], float] = time.monotonic
    wait_timeout_s: int = 600
    env: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if self.env is None:
            self.env = throwaway_secrets()

    def _compose(self, *args: str, timeout: float | None = None) -> CommandResult:
        command = ["docker", "compose", "-p", self.project]
        for file in self.files:
            command += ["-f", str(file)]
        result = self.runner(
            [*command, *args],
            cwd=self.root,
            env=dict(self.env or {}),
            timeout=timeout or float(self.wait_timeout_s + 60),
        )
        if result.returncode != 0:
            raise HarnessError(
                f"docker compose {' '.join(args)} failed ({result.returncode}): "
                f"{result.stderr.strip()[-2000:]}"
            )
        return result

    def build(self) -> float:
        started = self.clock()
        self._compose("pull", "--ignore-buildable")
        self._compose("build")
        return self.clock() - started

    def down(self) -> None:
        self._compose("down", "-v", "--remove-orphans")

    def up(self) -> float:
        started = self.clock()
        self._compose(
            "up",
            "-d",
            "--no-build",
            "--wait",
            "--wait-timeout",
            str(self.wait_timeout_s),
        )
        return self.clock() - started

    def image_ids(self) -> dict[str, str]:
        out = self._compose("images", "--format", "json").stdout.strip()
        rows = _json_rows(out)
        return {
            f"{row.get('Repository', '?')}:{row.get('Tag', '?')}": str(
                row.get("ID", "")
            )
            for row in rows
        }

    def exec_version(self, service: str, *command: str) -> str | None:
        try:
            out = self._compose("exec", "-T", service, *command, timeout=60)
        except HarnessError:
            return None
        text = (out.stdout or out.stderr).strip()
        return text.splitlines()[0] if text else None

    @property
    def admin_password(self) -> str:
        return (self.env or {})["SURGE_BOOTSTRAP_ADMIN_PASSWORD"]


def _json_rows(text: str) -> list[dict[str, Any]]:
    if not text:
        return []
    if text.startswith("["):
        loaded = json.loads(text)
        return [row for row in loaded if isinstance(row, dict)]
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def throwaway_secrets() -> dict[str, str]:
    """Per-run credentials for an isolated stack. Never written to a record."""
    return {
        "APP_JWT_SECRET": secrets.token_urlsafe(48),
        "DB_PASSWORD": secrets.token_urlsafe(24),
        "SURGE_BOOTSTRAP_ADMIN_USERNAME": "admin",
        "SURGE_BOOTSTRAP_ADMIN_PASSWORD": secrets.token_urlsafe(24),
    }


# --- Java API -------------------------------------------------------------------------


@dataclass
class SurgeApi:
    base_url: str
    transport: HttpTransport = urllib_transport
    timeout_s: float = 60.0
    token: str | None = None

    def _call(
        self,
        method: str,
        path: str,
        payload: object | None = None,
        *,
        raw: bytes | None = None,
        content_type: str = "application/json",
        expect: tuple[int, ...] = (200, 201),
    ) -> HttpResponse:
        headers = {"Accept": "application/json"}
        body = raw
        if payload is not None:
            body = json.dumps(payload).encode()
        if body is not None:
            headers["Content-Type"] = content_type
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        response = self.transport(
            method,
            self.base_url.rstrip("/") + path,
            headers=headers,
            body=body,
            timeout=self.timeout_s,
        )
        if response.status not in expect:
            raise HarnessError(
                f"{method} {path} answered {response.status}: "
                f"{response.body[:500].decode(errors='replace')}"
            )
        return response

    def login(self, username: str, password: str) -> None:
        body = self._call(
            "POST", "/api/v1/auth/login", {"username": username, "password": password}
        ).json()
        self.token = body["token"]

    def create_project(self, name: str) -> str:
        body = self._call(
            "POST", "/api/v1/projects", {"name": name, "description": "WP0B-8 evidence"}
        ).json()
        return str(body["id"])

    def import_geojson(self, project_id: str, geojson: bytes) -> dict[str, int]:
        body = self._call(
            "POST",
            f"/api/v1/projects/{project_id}/assets/geojson",
            raw=geojson,
        ).json()
        return {k: v for k, v in body.items() if isinstance(v, int)}

    def submit_job(self, project_id: str, scenario: str) -> str:
        body = self._call(
            "POST", f"/api/v1/projects/{project_id}/jobs", {"scenario": scenario}
        ).json()
        return str(body["id"])

    def job(self, project_id: str, job_id: str) -> dict[str, Any]:
        body: dict[str, Any] = self._call(
            "GET", f"/api/v1/projects/{project_id}/jobs/{job_id}"
        ).json()
        return body

    def feature_count(self, project_id: str, job_id: str, layer: str) -> int:
        body = self._call(
            "GET", f"/api/v1/projects/{project_id}/jobs/{job_id}/{layer}/geojson"
        ).json()
        return len(body.get("features") or [])


# --- measurement ----------------------------------------------------------------------


def _parse_instant(value: object) -> datetime | None:
    # Java writes ISO-8601 (write-dates-as-timestamps: false); epoch seconds
    # are accepted too, so a changed setting cannot silently drop a timing.
    if isinstance(value, int | float) and not isinstance(value, bool):
        return datetime.fromtimestamp(value, UTC)
    if not isinstance(value, str):
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _seconds_between(start: object, end: object) -> float | None:
    a, b = _parse_instant(start), _parse_instant(end)
    if a is None or b is None:
        return None
    return max(0.0, (b - a).total_seconds())


@dataclass
class Measurer:
    api: SurgeApi
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    poll_interval_s: float = 0.5
    job_timeout_s: float = 1800.0

    def run(self, project_id: str, variant: str, kind: RunKind) -> RunMeasurement:
        submitted = self.clock()
        job_id = self.api.submit_job(project_id, variant)
        while True:
            job = self.api.job(project_id, job_id)
            status = str(job.get("status"))
            if status in TERMINAL_STATUSES:
                terminal = self.clock()
                break
            if self.clock() - submitted > self.job_timeout_s:
                raise HarnessError(
                    f"job {job_id} still {status} after {self.job_timeout_s:.0f} s"
                )
            self.sleep(self.poll_interval_s)

        routes = poles = None
        persisted = None
        if status == "COMPLETED":
            routes = self.api.feature_count(project_id, job_id, "routes")
            poles = self.api.feature_count(project_id, job_id, "poles")
            persisted = self.clock() - submitted

        summary_text = job.get("resultSummaryJson")
        summary = json.loads(summary_text) if isinstance(summary_text, str) else None
        return RunMeasurement(
            request_variant=variant,
            kind=kind,
            job_id=job_id,
            job_status=status,
            submitted_to_terminal_s=terminal - submitted,
            submitted_to_persisted_s=persisted,
            server_queue_s=_seconds_between(job.get("createdAt"), job.get("startedAt")),
            server_run_s=_seconds_between(job.get("startedAt"), job.get("completedAt")),
            persisted_route_features=routes,
            persisted_pole_features=poles,
            error_message=job.get("errorMessage"),
            result_summary=summary,
        )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repository_revisions(root: Path, runner: CommandRunner = run_command) -> Revisions:
    def git(*args: str) -> str:
        result = runner(["git", *args], cwd=root, env={}, timeout=60)
        if result.returncode != 0:
            raise HarnessError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    return Revisions(
        revision=git("rev-parse", "HEAD"),
        clean_worktree=git("status", "--porcelain", "--untracked-files=no") == "",
        lockfile_sha256={
            name: sha256_file(root / name)
            for name in LOCKFILES
            if (root / name).exists()
        },
    )


def docker_environment(
    stack: ComposeStack, runner: CommandRunner = run_command
) -> Environment:
    info = runner(
        ["docker", "info", "--format", "{{json .}}"], cwd=stack.root, env={}, timeout=60
    )
    data: dict[str, Any] = {}
    if info.returncode == 0 and info.stdout.strip():
        data = json.loads(info.stdout)
    memory = data.get("MemTotal")
    return Environment(
        host_os=f"{platform.system()} {platform.release()}",
        docker_server_version=data.get("ServerVersion"),
        docker_cpus=data.get("NCPU"),
        docker_memory_gb=round(memory / 1024**3, 2)
        if isinstance(memory, int)
        else None,
        optimiser_python_version=stack.exec_version("optimizer", "python", "--version"),
        backend_java_version=stack.exec_version("backend", "java", "-version"),
        cold_definition=COLD_DEFINITION,
    )


def measure(
    *,
    stack: ComposeStack,
    api: SurgeApi,
    project_input: Path,
    variants: Sequence[str],
    warm_repeats: int = 1,
    build: bool = True,
    measurer: Measurer | None = None,
    record_id: str | None = None,
) -> MeasurementRecord:
    """Take one cold run and ``warm_repeats`` warm runs of every variant.

    Each variant gets its own clean stack, so every cold run really is the
    first submission after a clean start.
    """
    if not variants:
        raise ValueError("at least one request variant is required")
    if warm_repeats < 0:
        raise ValueError("warm_repeats must not be negative")
    measurer = measurer or Measurer(api)
    geojson = project_input.read_bytes()

    build_s = stack.build() if build else None
    runs: list[RunMeasurement] = []
    up_s: list[float] = []
    import_counts: dict[str, int] = {}
    for variant in variants:
        stack.down()
        up_s.append(stack.up())
        api.token = None
        api.login("admin", stack.admin_password)
        project_id = api.create_project(f"WP0B-8 {variant}")
        import_counts = api.import_geojson(project_id, geojson)
        runs.append(measurer.run(project_id, variant, "cold"))
        for _ in range(warm_repeats):
            runs.append(measurer.run(project_id, variant, "warm"))

    environment = docker_environment(stack, stack.runner)
    image_ids = stack.image_ids()
    stack.down()
    now = datetime.now(UTC)
    return MeasurementRecord(
        record_id=record_id or f"MSR-{now:%Y%m%dT%H%M%SZ}",
        created_at=now.isoformat(),
        blinded=False,
        project_input_sha256=hashlib.sha256(geojson).hexdigest(),
        import_counts=import_counts,
        revisions=repository_revisions(stack.root, stack.runner),
        environment=environment,
        stack=StackTimings(
            image_pull_build_s=build_s, compose_up_s=up_s, image_ids=image_ids
        ),
        poll_interval_s=measurer.poll_interval_s,
        runs=runs,
    )


def write_records(
    record: MeasurementRecord, *, raw_dir: Path, published_dir: Path, repo_root: Path
) -> tuple[Path, Path]:
    """Write the raw record outside the repository and the blinded one anywhere."""
    raw_dir = raw_dir.resolve()
    if raw_dir == repo_root.resolve() or repo_root.resolve() in raw_dir.parents:
        raise HarnessError(
            f"raw records carry unblinded results and must not be written inside the "
            f"repository ({raw_dir})"
        )
    raw_dir.mkdir(parents=True, exist_ok=True)
    published_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{record.record_id}.raw.json"
    published_path = published_dir / f"{record.record_id}.blinded.json"
    raw_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    published_path.write_text(
        record.blinded_copy().model_dump_json(indent=2), encoding="utf-8"
    )
    return raw_path, published_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WP0B-8 cold/warm measurement harness")
    parser.add_argument("--repo", type=Path, required=True, help="checkout to build")
    parser.add_argument("--project-input", type=Path, required=True, help="GeoJSON")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--published-dir", type=Path, required=True)
    parser.add_argument("--variant", action="append", dest="variants")
    parser.add_argument("--warm-repeats", type=int, default=1)
    parser.add_argument("--project-name", default="surge-evidence")
    parser.add_argument("--base-url", default="http://localhost:28080")
    parser.add_argument(
        "--override",
        type=Path,
        default=Path(__file__).with_name("compose.evidence-override.yml"),
    )
    parser.add_argument("--no-build", action="store_true")
    args = parser.parse_args(argv)

    stack = ComposeStack(
        root=args.repo,
        project=args.project_name,
        files=[args.repo / "docker-compose.yml", args.override.resolve()],
    )
    record = measure(
        stack=stack,
        api=SurgeApi(args.base_url),
        project_input=args.project_input,
        variants=args.variants or REQUEST_VARIANTS,
        warm_repeats=args.warm_repeats,
        build=not args.no_build,
    )
    raw, published = write_records(
        record,
        raw_dir=args.raw_dir,
        published_dir=args.published_dir,
        repo_root=Path(__file__).resolve().parents[3],
    )
    print(f"raw (access-controlled): {raw}")
    print(f"blinded: {published}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
