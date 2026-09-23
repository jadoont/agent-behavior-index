#!/usr/bin/env python3
"""Inventory raw pilot evidence without applying or changing preregistered metrics.

Container-rooted descendants are retained here. analysis.jibril's legacy
Runner.Worker filter is not sufficient to classify gh-aw Docker workloads.
This diagnostic deliberately does not assign proxies' remote hosts to clients.
"""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("sensor_log", type=Path)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
text = args.sensor_log.read_text(errors="replace")
decoder = json.JSONDecoder()
index = 0
inventory = {}
event_count = 0
while index < len(text):
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text):
        break
    try:
        event, index = decoder.raw_decode(text, index)
    except json.JSONDecodeError:
        # A pre-shutdown snapshot can end part-way through the final event.
        break
    event_count += 1
    if event.get("metadata", {}).get("format") != "flow":
        continue
    lineage = event.get("background", {}).get("ancestry", [])
    proc = event.get("process", {})
    if not lineage or lineage[-1].get("uuid") != proc.get("uuid"):
        lineage = [*lineage, proc]
    chain = tuple(p.get("cmd") or p.get("comm", "") for p in lineage)
    for flow in event.get("background", {}).get("flow_list", []):
        flags = flow.get("flags", {})
        if not flags.get("outgoing"):
            continue
        remote = flow.get("remote", {})
        address = remote.get("address", "")
        names = remote.get("names") or [address]
        port = flow.get("service_port") or remote.get("port")
        key = (chain, address, port, tuple(names))
        entry = inventory.setdefault(key, {
            "chain": list(chain), "process": proc.get("cmd"),
            "exe": proc.get("exe"), "pid": proc.get("pid"),
            "remote_address": address, "remote_names": names, "port": port,
            "protocol": flow.get("proto"), "first_event": event.get("timestamp"),
            "last_event": event.get("timestamp"), "event_observations": 0,
            "bidirectional_observed": False,
            "container_rooted": any("containerd-shim" in p for p in chain),
        })
        entry["event_observations"] += 1
        entry["last_event"] = event.get("timestamp")
        entry["bidirectional_observed"] |= bool(flags.get("ingress") and flags.get("egress"))

payload = {
    "sensor_file": args.sensor_log.name,
    "decoded_events": event_count,
    "unique_chain_address_port_names": len(inventory),
    "unconsumed_nonwhitespace_bytes": len(text[index:].strip()),
    "method": "Raw inventory; not preregistered scoring or proxy attribution",
    "edges": sorted(inventory.values(), key=lambda e: (e["chain"], e["remote_address"], str(e["port"]))),
}
args.output.write_text(json.dumps(payload, indent=2) + "\n")
print(json.dumps({k: v for k, v in payload.items() if k != "edges"}))
