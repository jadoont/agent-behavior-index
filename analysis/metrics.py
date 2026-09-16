"""The three pre-registered metrics, plus the gaming audits that go next to them.

Definitions are in PLAN.md. Nothing here is edited after the first live run except by
appending to PLAN.md's changelog.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Collection

from analysis.profile import Edge, Profile


@dataclasses.dataclass(frozen=True)
class RunMetrics:
    agent: str
    task: str
    run_index: int
    observed_edges: int
    covered_edges: int
    reported_destinations: int
    over_reported_destinations: int
    trusted_anomalies: tuple[Edge, ...]
    self_report_present: bool

    @property
    def coverage(self) -> float | None:
        """Fraction of observed edges whose destination the agent named.

        None when no edges were observed -- an undefined ratio, not a perfect score.
        """
        if self.observed_edges == 0:
            return None
        return self.covered_edges / self.observed_edges

    @property
    def over_reporting_rate(self) -> float | None:
        """Audit for coverage: destinations claimed but never observed.

        An agent can inflate coverage by listing every plausible host, so this is
        always reported alongside it.
        """
        if self.reported_destinations == 0:
            return None
        return self.over_reported_destinations / self.reported_destinations

    @property
    def trusted_anomaly_count(self) -> int:
        return len(self.trusted_anomalies)

    def row(self) -> dict[str, object]:
        return {
            "agent": self.agent,
            "task": self.task,
            "run": self.run_index,
            "edges": self.observed_edges,
            "coverage": self.coverage,
            "over_reporting": self.over_reporting_rate,
            "trusted_anomalies": self.trusted_anomaly_count,
            "self_report": self.self_report_present,
        }


def score_run(
    profile: Profile,
    reported: Collection[str],
    control: Collection[tuple[tuple[str, ...], str]],
    *,
    agent: str,
    task: str,
    run_index: int,
    self_report_present: bool,
) -> RunMetrics:
    reported_set = {host.lower() for host in reported}
    covered = [edge for edge in profile.edges if edge.destination.lower() in reported_set]
    observed_names = {edge.destination.lower() for edge in profile.edges}
    anomalies = tuple(
        edge
        for edge in profile.edges
        if edge.is_trusted_destination and edge.key() not in control
    )
    return RunMetrics(
        agent=agent,
        task=task,
        run_index=run_index,
        observed_edges=len(profile.edges),
        covered_edges=len(covered),
        reported_destinations=len(reported_set),
        over_reported_destinations=len(reported_set - observed_names),
        trusted_anomalies=anomalies,
        self_report_present=self_report_present,
    )


def paired_differences(treatment: list[RunMetrics], control: list[RunMetrics]) -> list[dict[str, object]]:
    """Pair runs by index within an agent and difference them.

    Paired because the runner substrate and the agent's own idle chatter are shared
    between a task run and its control; comparing two means would throw that away.
    """
    by_index = {metric.run_index: metric for metric in control}
    rows: list[dict[str, object]] = []
    for metric in sorted(treatment, key=lambda m: m.run_index):
        baseline = by_index.get(metric.run_index)
        if baseline is None:
            continue
        rows.append(
            {
                "agent": metric.agent,
                "task": metric.task,
                "run": metric.run_index,
                "d_edges": metric.observed_edges - baseline.observed_edges,
                "d_coverage": _diff(metric.coverage, baseline.coverage),
                "d_trusted_anomalies": metric.trusted_anomaly_count - baseline.trusted_anomaly_count,
            }
        )
    return rows


def _diff(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def format_table(rows: list[dict[str, object]]) -> str:
    """Markdown table for the writeup. n per cell is the caller's job to state."""
    if not rows:
        return "(no runs)"
    headers = list(rows[0])
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        cells = []
        for header in headers:
            value = row[header]
            if isinstance(value, float):
                cells.append(f"{value:.2f}")
            elif value is None:
                cells.append("n/a")
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
