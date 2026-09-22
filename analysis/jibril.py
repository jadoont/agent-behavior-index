"""Parse raw Jibril events (`/var/log/jibril.out`, uploaded when the Garnet action runs
with `debug: true`) into the same Profile/Edge set as the public Execution Profile.

The file is a stream of pretty-printed JSON objects. Each `flow` event carries the
initiating process, its full ancestry, and a `flow_list` of connections with kernel
flags, so it is a superset of what the public profile exposes and does not depend on
the run being made public.
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
from collections.abc import Iterator

from analysis.profile import (
    METADATA_ADDRESSES,
    RUNNER_ROOT,
    SENSOR_HOSTS,
    Edge,
    Profile,
    _dedupe,
)

# Azure wire-server / instance metadata used by the hosted runner itself.
_RUNNER_INFRA_ADDRESSES = METADATA_ADDRESSES | {"168.63.129.16"}
# Executables bundled with the Actions runner (its own node for JS actions, log and
# artifact upload). Anything the workload installs lives elsewhere (/usr, /opt/hostedtoolcache).
_RUNNER_BUNDLED_EXE = "/actions-runner/"


@dataclasses.dataclass(frozen=True)
class Flow:
    """One kernel-observed connection, before the edge filters."""

    edge: Edge
    remote_address: str
    port: int
    completed: bool  # traffic seen in both directions
    scaffolding: bool  # runner-owned process chain, not workload


def iter_events(text: str) -> Iterator[dict]:
    decoder = json.JSONDecoder()
    index = 0
    while index < len(text):
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            return
        event, index = decoder.raw_decode(text, index)
        yield event


def _lineage(event: dict) -> list[dict]:
    ancestry = event.get("background", {}).get("ancestry", [])
    process = event.get("process", {})
    if not ancestry or ancestry[-1].get("uuid") != process.get("uuid"):
        ancestry = [*ancestry, process]
    return ancestry


def _ancestry(lineage: list[dict]) -> tuple[str, ...]:
    chain = [proc.get("cmd") or proc.get("comm", "") for proc in lineage]
    if RUNNER_ROOT in chain:
        chain = chain[chain.index(RUNNER_ROOT) :]
    return tuple(chain)


def _is_scaffolding(lineage: list[dict]) -> bool:
    """Keep host workloads and gh-aw's explicitly rooted container workload.

    Container processes are reparented to containerd-shim, not Runner.Worker.
    Only the awf-cmd workload subtree is retained; sibling proxy, gateway, health
    check and firewall containers remain scaffolding. This is not proxy stitching.
    """
    names = [proc.get("cmd") or proc.get("comm", "") for proc in lineage]
    if RUNNER_ROOT not in names:
        container = any(name.startswith("containerd-shim") for name in names)
        workload = any(
            name.startswith("awf-cmd-") and name.endswith(".sh") for name in names
        )
        return not (container and workload)
    below = lineage[names.index(RUNNER_ROOT) + 1 :]
    return all(_RUNNER_BUNDLED_EXE in proc.get("exe", "") for proc in below)


def _destination(remote: dict) -> str:
    names = [name for name in remote.get("names", []) if name != remote.get("address")]
    # Jibril lists CNAME intermediates before the queried hostname; the last is the
    # name the process actually asked for.
    return names[-1] if names else remote.get("address", "")


def flows(text: str) -> list[Flow]:
    result: list[Flow] = []
    for event in iter_events(text):
        if event.get("metadata", {}).get("format") != "flow":
            continue
        lineage = _lineage(event)
        ancestry = _ancestry(lineage)
        scaffolding = _is_scaffolding(lineage)
        step = event.get("scenarios", {}).get("github", {}).get("action", "")
        for flow in event.get("background", {}).get("flow_list", []):
            flags = flow.get("flags", {})
            if not flags.get("outgoing"):
                continue
            remote = flow.get("remote", {})
            result.append(
                Flow(
                    edge=Edge(
                        destination=_destination(remote),
                        ancestry=ancestry,
                        process=ancestry[-1] if ancestry else "",
                        step=step,
                        protocol=flow.get("proto", ""),
                    ),
                    remote_address=remote.get("address", ""),
                    port=int(flow.get("service_port") or remote.get("port") or 0),
                    completed=bool(flags.get("ingress") and flags.get("egress")),
                    scaffolding=scaffolding,
                )
            )
    return result


def _keep(flow: Flow) -> bool:
    # The step label on raw flow events is unreliable (it reflects when the process
    # was first seen), so lineage alone decides what is scaffolding.
    if flow.scaffolding:
        return False
    if flow.port == 53 or flow.remote_address in _RUNNER_INFRA_ADDRESSES:
        return False
    if flow.remote_address.startswith("127.") or flow.remote_address == "::1":
        return False
    return flow.edge.destination not in SENSOR_HOSTS


def parse_jibril(text: str, run_id: str = "", commit_sha: str = "") -> Profile:
    kept = [flow for flow in flows(text) if _keep(flow)]
    github = next(
        (e.get("scenarios", {}).get("github", {}) for e in iter_events(text) if "scenarios" in e), {}
    )
    return Profile(
        run_id=run_id or str(github.get("run_id", "")),
        profile_id="jibril-debug",
        repository=github.get("repository", ""),
        workflow=github.get("workflow", ""),
        job=github.get("job", ""),
        commit_sha=commit_sha or github.get("sha", ""),
        edges=_dedupe(flow.edge for flow in kept),
    )


def load_jibril(path: str | pathlib.Path) -> Profile:
    return parse_jibril(pathlib.Path(path).read_text())


def attempted_only(text: str) -> list[Flow]:
    """Outgoing flows with egress but no ingress: candidates for refused/blocked connections."""
    return [flow for flow in flows(text) if _keep(flow) and not flow.completed]
