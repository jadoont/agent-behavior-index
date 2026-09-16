"""Parse a Garnet public Execution Profile into the edge set used by every metric.

Schema: runtime-review-public/v3, from
    https://app.garnet.ai/api/public/runs/<run-id>?profile=<profile-id>

An edge is (ancestry, destination). Filters are defined in PLAN.md and applied
identically to every run; changing them changes every metric, so they live here and
nowhere else.
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import urllib.request
from collections.abc import Iterable, Sequence

RUNNER_ROOT = "Runner.Worker"
SCAFFOLDING_STEP = "99. Runner Processes"
SENSOR_HOSTS = frozenset({"api.garnet.ai"})
METADATA_ADDRESSES = frozenset({"169.254.169.254", "169.254.170.2", "fd00:ec2::254"})

# Frozen at pre-registration. Do not edit after the first live run.
TRUSTED_DESTINATIONS = frozenset(
    {
        "github.com",
        "api.github.com",
        "codeload.github.com",
        "objects.githubusercontent.com",
        "raw.githubusercontent.com",
        "release-assets.githubusercontent.com",
        "registry.npmjs.org",
        "pypi.org",
        "files.pythonhosted.org",
    }
)

API_TEMPLATE = "https://app.garnet.ai/api/public/runs/{run_id}?profile={profile_id}"


@dataclasses.dataclass(frozen=True)
class Edge:
    destination: str
    ancestry: tuple[str, ...]
    process: str
    step: str
    protocol: str

    @property
    def chain(self) -> str:
        return " -> ".join(self.ancestry)

    @property
    def is_trusted_destination(self) -> bool:
        return self.destination in TRUSTED_DESTINATIONS

    def key(self) -> tuple[tuple[str, ...], str]:
        """Identity for control-set comparison: the chain and where it went."""
        return (self.ancestry, self.destination)


@dataclasses.dataclass(frozen=True)
class Profile:
    run_id: str
    profile_id: str
    repository: str
    workflow: str
    job: str
    commit_sha: str
    edges: tuple[Edge, ...]

    @property
    def destinations(self) -> frozenset[str]:
        return frozenset(edge.destination for edge in self.edges)


def _is_dns(association: dict) -> bool:
    return any(port.startswith("53") for port in association.get("remote_ports", []))


def _is_metadata(association: dict) -> bool:
    return association.get("remote_address") in METADATA_ADDRESSES


def _destination(association: dict) -> str:
    names = association.get("remote_names") or []
    return names[0] if names else association.get("remote_address", "")


def _ancestry(association: dict) -> tuple[str, ...]:
    ancestry = list(association.get("ancestry", []))
    if RUNNER_ROOT in ancestry:
        ancestry = ancestry[ancestry.index(RUNNER_ROOT) :]
    return tuple(ancestry)


def _keep(association: dict) -> bool:
    if association.get("github_step") == SCAFFOLDING_STEP:
        return False
    if _is_dns(association) or _is_metadata(association):
        return False
    return _destination(association) not in SENSOR_HOSTS


def parse_profile(payload: dict) -> Profile:
    """Build a Profile from the JSON body of one public-run response."""
    profiles = payload.get("profiles") or []
    if not profiles:
        raise ValueError("no profiles in payload")
    if len(profiles) > 1:
        raise ValueError(f"expected one profile, got {len(profiles)}")
    profile = profiles[0]
    run = profile["run"]
    edges = tuple(
        Edge(
            destination=_destination(association),
            ancestry=_ancestry(association),
            process=association.get("process", ""),
            step=association.get("github_step", ""),
            protocol=association.get("protocol", ""),
        )
        for association in profile["associations"]
        if _keep(association)
    )
    return Profile(
        run_id=str(run["run_id"]),
        profile_id=run["profile_id"],
        repository=run["repository"],
        workflow=run["workflow"],
        job=run["job"],
        commit_sha=run["commit_sha"],
        edges=_dedupe(edges),
    )


def _dedupe(edges: Iterable[Edge]) -> tuple[Edge, ...]:
    """One edge per (chain, destination); repeated flows are not independent evidence."""
    seen: dict[tuple[tuple[str, ...], str], Edge] = {}
    for edge in edges:
        seen.setdefault(edge.key(), edge)
    return tuple(seen.values())


def load_profile(path: str | pathlib.Path) -> Profile:
    return parse_profile(json.loads(pathlib.Path(path).read_text()))


def fetch_profile(run_id: str, profile_id: str, timeout: float = 30.0) -> Profile:
    url = API_TEMPLATE.format(run_id=run_id, profile_id=profile_id)
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return parse_profile(json.load(response))


def control_edges(profiles: Sequence[Profile], min_runs: int = 2) -> frozenset[tuple[tuple[str, ...], str]]:
    """Edges that count as baseline: present in at least `min_runs` control profiles.

    Requiring repetition keeps one noisy control run from suppressing a real anomaly.
    """
    counts: dict[tuple[tuple[str, ...], str], int] = {}
    for profile in profiles:
        for key in {edge.key() for edge in profile.edges}:
            counts[key] = counts.get(key, 0) + 1
    return frozenset(key for key, count in counts.items() if count >= min_runs)
