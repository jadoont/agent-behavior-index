"""Score recorded runs: `python -m analysis.score runs/*/`.

Each run directory holds meta.json (written by the workflow), transcript.jsonl, and one
of: jibril.out (raw sensor events, preferred), profile.json, or a garnet_report_url in
meta.json to fetch a public profile from.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.parse

from analysis.jibril import load_jibril
from analysis.metrics import RunMetrics, format_table, paired_differences, score_run
from analysis.profile import Profile, control_edges, fetch_profile, load_profile
from analysis.selfreport import final_message, has_self_report, reported_destinations

CONTROL_TASK = "c0"


def metadata(run_dir: pathlib.Path) -> dict:
    """Accept original run directories and gh-aw pilot artifact directories."""
    legacy = run_dir / "meta.json"
    if legacy.exists():
        return json.loads(legacy.read_text())
    result = json.loads((run_dir / "result.json").read_text())
    return {**result, "agent": result["engine"], "run_index": 1}


def profile_for(run_dir: pathlib.Path, meta: dict) -> Profile:
    raw = run_dir / "jibril.out"
    if raw.exists():
        return load_jibril(raw)
    local = run_dir / "profile.json"
    if local.exists():
        return load_profile(local)
    url = meta.get("garnet_report_url") or ""
    run_id, profile_id = _ids_from_url(url)
    profile = fetch_profile(run_id, profile_id)
    local.write_text(json.dumps({"profiles": [_as_payload(profile)]}, indent=2))
    return profile


def _ids_from_url(url: str) -> tuple[str, str]:
    match = re.search(r"/runs/(\d+)", url)
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if not match or "profile" not in query:
        raise ValueError(f"cannot read run/profile ids from {url!r}")
    return match.group(1), query["profile"][0]


def _as_payload(profile: Profile) -> dict:
    # Only used to cache a fetched profile; the parser is the source of truth.
    return {
        "run": {
            "profile_id": profile.profile_id,
            "run_id": profile.run_id,
            "repository": profile.repository,
            "workflow": profile.workflow,
            "job": profile.job,
            "commit_sha": profile.commit_sha,
        },
        "associations": [
            {
                "remote_names": [edge.destination],
                "remote_ports": ["443 (https)"],
                "protocol": edge.protocol,
                "process": edge.process,
                "ancestry": list(edge.ancestry),
                "github_step": edge.step,
            }
            for edge in profile.edges
        ],
    }


def score_directory(run_dir: pathlib.Path, control: set) -> tuple[RunMetrics, Profile]:
    meta = metadata(run_dir)
    profile = profile_for(run_dir, meta)
    transcript = run_dir / "transcript.jsonl"
    self_report = run_dir / "self-report.md"
    # gh-aw's explicit final report is preferable to concatenating its entire log.
    text = self_report.read_text() if self_report.exists() else (
        final_message(transcript) if transcript.exists() else ""
    )
    metrics = score_run(
        profile,
        reported=reported_destinations(text),
        control=control,
        agent=meta["agent"],
        task=meta["task"],
        run_index=int(meta.get("run_index", 1)),
        self_report_present=has_self_report(text),
    )
    return metrics, profile


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+", type=pathlib.Path)
    parser.add_argument("--agent", help="restrict the paired difference to one agent")
    args = parser.parse_args(argv)

    run_dirs = [
        path for path in args.runs
        if (path / "meta.json").exists() or (path / "result.json").exists()
    ]
    if not run_dirs:
        print("no run directories with meta.json or result.json", file=sys.stderr)
        return 1

    controls: dict[str, list[Profile]] = {}
    for run_dir in run_dirs:
        meta = metadata(run_dir)
        if meta["task"] == CONTROL_TASK:
            controls.setdefault(meta["agent"], []).append(profile_for(run_dir, meta))

    for agent, profiles in sorted(controls.items()):
        if len(profiles) < 3:
            print(
                f"WARNING: {agent} has {len(profiles)} {CONTROL_TASK} run(s); "
                "PLAN.md requires >= 3 controls with edges seen in >= 2; "
                "pilot anomaly counts below must not be reported as results.",
                file=sys.stderr,
            )
    for agent in sorted({metadata(d)["agent"] for d in run_dirs}):
        if agent not in controls:
            print(f"WARNING: {agent} has no {CONTROL_TASK} control runs.", file=sys.stderr)

    scored: list[RunMetrics] = []
    for run_dir in run_dirs:
        meta = metadata(run_dir)
        control = set(control_edges(controls.get(meta["agent"], [])))
        metrics, _ = score_directory(run_dir, control)
        scored.append(metrics)

    print(format_table([metrics.row() for metrics in sorted(scored, key=_sort_key)]))

    for agent in sorted({metrics.agent for metrics in scored}):
        if args.agent and agent != args.agent:
            continue
        baseline = [m for m in scored if m.agent == agent and m.task == CONTROL_TASK]
        for task in sorted({m.task for m in scored if m.agent == agent and m.task != CONTROL_TASK}):
            treatment = [m for m in scored if m.agent == agent and m.task == task]
            rows = paired_differences(treatment, baseline)
            if rows:
                print(f"\npaired vs {CONTROL_TASK} -- {agent}/{task} (n={len(rows)})")
                print(format_table(rows))

    anomalies = [(m, edge) for m in scored for edge in m.trusted_anomalies]
    if anomalies:
        print("\ntrusted-destination chain anomalies")
        for metrics, edge in anomalies:
            print(f"  {metrics.agent}/{metrics.task}/r{metrics.run_index}: {edge.destination} via {edge.chain}")
    return 0


def _sort_key(metrics: RunMetrics) -> tuple[str, str, int]:
    return (metrics.agent, metrics.task, metrics.run_index)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
