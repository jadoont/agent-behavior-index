#!/usr/bin/env python3
"""Validate PR experiment definitions and post receipts, never execute artifacts."""
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
ROOT = Path(__file__).resolve().parents[1]


def gh(*args, binary=False):
    return subprocess.check_output(["gh", *args], text=not binary)


def validate_definition(path, document):
    if not NAME.fullmatch(path.stem):
        raise ValueError("Experiment filename must be a lowercase slug.")
    if set(document) != {"id", "agent", "task", "purpose"}:
        raise ValueError("Exactly id, agent, task and purpose are required.")
    if document["id"] != path.stem:
        raise ValueError("Experiment id must match its filename.")
    if document["agent"] != "claude":
        raise ValueError("Only the verified Claude arm is enabled.")
    if document["task"] not in {"c0", "t2"}:
        raise ValueError("Only the bounded C0 and T2 fixtures are enabled.")
    if not isinstance(document["purpose"], str) or not 10 <= len(document["purpose"]) <= 1000:
        raise ValueError("Purpose must be 10-1000 characters.")
    return document


def validate():
    repo, pr = os.environ["GITHUB_REPOSITORY"], int(os.environ["ABI_PR"])
    pages = json.loads(gh("api", f"repos/{repo}/pulls/{pr}/files",
                         "--paginate", "--slurp"))
    files = [row for page in pages for row in page]
    selected = [
        row["filename"] for row in files
        if re.fullmatch(r"experiments/[a-z0-9-]+\.json", row["filename"])
        and row["status"] != "removed"
    ]
    if len(selected) != 1:
        raise ValueError("An experiment PR must add or change exactly one experiments/*.json.")
    path = ROOT / selected[0]
    if path.is_symlink() or path.stat().st_size > 4096:
        raise ValueError("Experiment definition must be a small regular JSON file.")
    doc = validate_definition(path, json.loads(path.read_text()))
    with open(os.environ["GITHUB_OUTPUT"], "a") as out:
        out.write(f"task={doc['task']}\nexperiment={doc['id']}\n")
    print(f"Validated {doc['id']}: claude/{doc['task']}, one bounded run.")


def receipt():
    repo, run = os.environ["GITHUB_REPOSITORY"], int(os.environ["GITHUB_RUN_ID"])
    attempt, pr = int(os.environ["GITHUB_RUN_ATTEMPT"]), int(os.environ["ABI_PR"])
    run_url = f"https://github.com/{repo}/actions/runs/{run}"
    artifacts = json.loads(gh("api", f"repos/{repo}/actions/runs/{run}/artifacts?per_page=100"))
    prefix = f"abi-claude-{os.environ['ABI_TASK']}-{run}-{attempt}"
    matches = [a for a in artifacts["artifacts"] if a["name"] == prefix]
    result = None
    if len(matches) == 1:
        # Only parse a tiny whitelisted JSON member; never extract or execute files.
        archive = gh("api", f"repos/{repo}/actions/artifacts/{matches[0]['id']}/zip", binary=True)
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            info = z.getinfo("result.json")
            if info.file_size > 65536:
                raise ValueError("Oversized result.json")
            result = json.loads(z.read(info))
        if str(result["github_run_id"]) != str(run) or result["task"] != os.environ["ABI_TASK"]:
            raise ValueError("Artifact identity does not match this run.")
    jobs = json.loads(gh("api", f"repos/{repo}/actions/runs/{run}/jobs?per_page=100"))
    urls = set()
    pattern = re.compile(
        rf"https://app\.garnet\.ai/public/runs/{run}\?profile=[a-f0-9-]{{36}}"
    )
    for job in jobs["jobs"]:
        if job["name"].endswith(" / agent"):
            log = gh("api", "--allow-escape-sequences", f"repos/{repo}/actions/jobs/{job['id']}/logs")
            urls.update(pattern.findall(log))
    status = lambda key: "PASS" if result and result.get(key) is True else "NOT VERIFIED / FAIL"
    body = [
        f"<!-- abi-receipt:{run}:{attempt} -->",
        f"## ABI experiment: {os.environ['ABI_EXPERIMENT']}",
        f"PR head: `{os.environ['ABI_HEAD_SHA']}`",
        f"Task: `claude/{os.environ['ABI_TASK']}` · Model: `claude-sonnet-4-6`",
        f"Workflow: **{os.environ['ABI_JOB_RESULT']}** · [Run and artifacts]({run_url})",
        "",
        "| Independent check | Result |", "| --- | --- |",
        f"| Functional output | {status('task_pass')} |",
        f"| Required task protocol | {status('protocol_pass')} |",
        f"| Self-report captured | {status('self_report_captured')} |",
        f"| Execution gate | {status('pilot_pass')} |",
        "",
    ]
    if result:
        for title, value in (
            ("Trigger SHA (GitHub merge ref on PRs)", result.get("commit")),
            ("Checked-out revision", result.get("checkout_commit")),
        ):
            if isinstance(value, str) and re.fullmatch("[a-f0-9]{40}", value):
                body.append(f"{title}: `{value}`.")
    body += [f"[Exact Garnet profile]({url})" for url in sorted(urls)]
    if not urls:
        body.append("Exact Garnet profile not verified. Do not interpret a green job as recording proof.")
    body += [
        "",
        "This is a pilot receipt, not a benchmark score. A functional pass does not prove",
        "install-hook execution, network attribution, or a stable control baseline.",
        "Review the self-report, diff and kernel evidence in the run artifacts.",
        "Garnet authentication uses OIDC; no long-lived Garnet token is passed.",
    ]
    text = "\n".join(body) + "\n"
    Path(os.environ["GITHUB_STEP_SUMMARY"]).write_text(text)
    # Retry of the same run/attempt updates only this workflow's own marked comment.
    pages = json.loads(gh("api", f"repos/{repo}/issues/{pr}/comments", "--paginate", "--slurp"))
    marker = body[0]
    existing = [
        c for page in pages for c in page
        if c["user"]["login"] == "github-actions[bot]" and marker in c["body"]
    ]
    endpoint = f"repos/{repo}/issues/comments/{existing[0]['id']}" if existing else f"repos/{repo}/issues/{pr}/comments"
    subprocess.run(
        ["gh", "api", endpoint, "--method", "PATCH" if existing else "POST", "--input", "-"],
        input=json.dumps({"body": text}), text=True, check=True, stdout=subprocess.DEVNULL,
    )
    print(f"Attached receipt to PR #{pr}.")


if __name__ == "__main__":
    {"validate": validate, "receipt": receipt}[sys.argv[1]]()
