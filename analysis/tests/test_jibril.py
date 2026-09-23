"""Raw Jibril parser, tested against a real debug artifact from run 35064188350
(agent=none, task=c0) with loopback-only flow events and file lists stripped."""

import json
import pathlib

from analysis.jibril import _is_scaffolding, attempted_only, flows, parse_jibril

FIXTURE = pathlib.Path(__file__).parent.parent / "fixtures" / "jibril_c0_none.out"
TEXT = FIXTURE.read_text()


def test_run_metadata_comes_from_profile_event():
    profile = parse_jibril(TEXT)
    assert profile.run_id == "35064188350"
    assert profile.repository == "jadoont/agent-behavior-index"
    assert profile.job == "record"
    assert profile.commit_sha.startswith("bcf22d0e")


def test_workload_edges_are_pip_to_pypi_only():
    profile = parse_jibril(TEXT)
    assert profile.destinations == {"pypi.org", "files.pythonhosted.org"}
    assert {edge.chain for edge in profile.edges} == {"Runner.Worker -> bash -> pip"}


def test_scaffolding_dns_and_azure_wireserver_are_filtered():
    raw = {flow.edge.destination for flow in flows(TEXT)}
    kept = parse_jibril(TEXT).destinations
    assert "productionresultssa3.blob.core.windows.net" in raw and "productionresultssa3.blob.core.windows.net" not in kept
    assert "168.63.129.16" in raw and "168.63.129.16" not in kept
    assert not any(flow.port == 53 and flow.edge.destination in kept for flow in flows(TEXT))


def _without_step_labels(text: str) -> str:
    return text.replace('"action": "99. Runner Processes"', '"action": ""')


def test_scaffolding_classified_by_lineage_not_step_label():
    stripped = _without_step_labels(TEXT)
    assert "99. Runner Processes" not in stripped
    assert parse_jibril(stripped).destinations == {"pypi.org", "files.pythonhosted.org"}
    runner_node = [f for f in flows(stripped) if f.edge.chain == "Runner.Worker -> node"]
    assert runner_node and all(f.scaffolding for f in runner_node)
    waagent = [f for f in flows(stripped) if f.edge.chain.startswith("systemd")]
    assert waagent and all(f.scaffolding for f in waagent)


def test_workload_node_under_bash_is_not_scaffolding():
    event = json.dumps(
        {
            "metadata": {"format": "flow"},
            "background": {
                "ancestry": [
                    {"uuid": "a", "cmd": "Runner.Worker", "exe": "/home/runner/actions-runner/bin/Runner.Worker"},
                    {"uuid": "b", "cmd": "bash", "exe": "/usr/bin/bash"},
                    {"uuid": "c", "cmd": "npm", "exe": "/opt/hostedtoolcache/node/22/x64/bin/node"},
                ],
                "flow_list": [
                    {
                        "proto": "TCP",
                        "remote": {"address": "140.82.112.5", "names": ["140.82.112.5", "api.github.com"], "port": 443},
                        "service_port": 443,
                        "flags": {"outgoing": True, "ingress": True, "egress": True},
                    }
                ],
            },
            "process": {"uuid": "d", "cmd": "node", "exe": "/opt/hostedtoolcache/node/22/x64/bin/node"},
            "scenarios": {"github": {"action": "99. Runner Processes"}},
        }
    )
    # a misleading scaffolding step label must not hide a workload edge
    assert [(e.destination, e.chain) for e in parse_jibril(event).edges] == [
        ("api.github.com", "Runner.Worker -> bash -> npm -> node")
    ]


def test_process_is_not_duplicated_at_chain_tail():
    for edge in parse_jibril(TEXT).edges:
        assert edge.ancestry[-1] != edge.ancestry[-2]


def test_control_run_has_no_attempted_only_flows():
    assert attempted_only(TEXT) == []


def test_ghaw_container_workload_is_not_dropped():
    lineage = [{"cmd": name} for name in [
        "systemd", "containerd-shim-runc-v2", "entrypoint.sh", "awf-cmd-1.sh",
        "node", "claude.exe", "bash", "npm install", "sh", "node",
    ]]
    assert not _is_scaffolding(lineage)


def test_ghaw_sibling_harness_containers_remain_scaffolding():
    for tail in [
        ["squid"], ["awmg"], ["node"],
        ["entrypoint.sh", "api-proxy-health-check.sh", "timeout", "bash", "cat"],
        ["touch", "setup-iptables.sh", "getent"],
    ]:
        assert _is_scaffolding([
            {"cmd": name} for name in ["systemd", "containerd-shim-runc-v2", *tail]
        ])


def test_host_process_named_like_workload_does_not_bypass_filter():
    assert _is_scaffolding([{"cmd": "systemd"}, {"cmd": "awf-cmd-1.sh"}])
