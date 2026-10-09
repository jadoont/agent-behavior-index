# Agent Behavior Index: trace and execution evidence

This is a **dataset-card draft**, pending source and privacy review. It describes a
release format; it does not claim that a benchmark or the planned six-run study
has been completed. Confirm the HF account, license and consent before uploading.

## Question

When a coding agent works on a bounded repository task, which parts of its
execution are visible in its own trace, in gh-aw's boundary logs, and in an
independent kernel recorder? A difference between these views is a measurement,
not automatically evidence of deception. An accurate self-report and a run with
no task egress are retained.

## Experimental setup

The agent runs in gh-aw on GitHub Actions. The control task (C0) asks it to fix a
test failure. T2 is an archived install-hook pilot. T3 repeats C0's bug and tests
and adds a pytest-session hook that requests `api.github.com/zen` through the
existing Squid proxy. The independent T3 check disables conftest loading, so the
check cannot itself generate the experimental traffic. T3 is currently a
prospective experiment: do not imply a new T3 run has completed until the
receipts are attached. Each run keeps its functional, protocol and self-report
results separately.

The unit of independent observation is a deduplicated
**(process ancestry, destination)** association. See `analysis/profile.py` for
the frozen filters and `PLAN.md` for the control-set and paired comparison rules.
A CONNECT in Squid is a proxy contact, not proof that an HTTP GET completed or
that a particular agent child process caused the outbound request. An edge to
the proxy and an outbound edge from Squid are **not** an attributed end-to-end
chain. Mark the join unknown without connection IDs or validated proxy evidence.

## Files per run

- `session.jsonl`: HF Session Trace Simple Format. The first line is the
  `session` header; following lines are captured user, assistant and tool
  messages. A captured gh-aw prompt is explicitly marked in the header as a
  harness artifact. Native call/result IDs are preserved. The public STS viewer
  may need HF to register the `gh-aw` harness name for branding.
- `said.json`: the agent-written self-report captured by the independent
  checker, when its evidence artifact is supplied; otherwise, explicitly
  labeled assistant text or a successful Write-call input. A Write input does
  not independently establish the final file contents.
- `harness.json`: Squid CONNECT metadata, count of API-proxy and MCP RPC log
  records, and observed MCP URL domains. A missing log is marked unavailable,
  not zero. No proxy request is silently turned into an agent action.
- `kernel.json`: associations in the Garnet public profile, using the
  pre-registered parser. An optional separate raw Jibril inventory is labeled
  distinctly. Profile summaries do not restore lost connection identity.
- `reconciliation.json` and `.csv`: one diagnostic row per run, including
  availability, attribution state, tool activity, claimed destinations,
  independent task/protocol checks when supplied, and observed edges.
  Counts of Bash inputs mentioning pytest and explicit conftest Read attempts
  are transcript markers, not proof that a command or hook executed.
- `manifest.json`: run/profile URLs, run attempt and SHA sources when provided,
  SHA-256 of each source and artifact member, native source-line mapping,
  transformation/redaction counts, and review status.

Neither a nonempty sensor file nor a green GitHub run is evidence of task-level
network coverage. A profile can be valid while containing no task edge. A
missing Squid log means unknown, not no contact. A proposed connection is
unattributed until the proxy can be joined with independent fields.

## Reproduce a private bundle

Download the agent artifact and ABI evidence for one GitHub Actions run. Retrieve
the Garnet public JSON for the *exact* profile ID on that run:

```bash
RUN_ID=... PROFILE_ID=...
gh api "repos/jadoont/agent-behavior-index/actions/runs/$RUN_ID" > github-run.json
curl -fsSL "https://app.garnet.ai/api/public/runs/$RUN_ID?profile=$PROFILE_ID" -o profile.json
python -m analysis.reconcile \
  --profile profile.json --task c0 --agent-artifact agent.zip \
  --github-run github-run.json --result result.json \
  --evidence-artifact abi-evidence.zip \
  --agent-descriptor agent-artifact.json --evidence-descriptor evidence-artifact.json \
  --output private-exhibit/$RUN_ID
```

`agent.zip` is gh-aw's agent artifact, with `agent-stdio.log` and
`sandbox/firewall/logs/access.log`. `result.json` comes from the corresponding
ABI evidence artifact; supplying it is optional, but missing check fields
remain unknown. If only the ABI evidence artifact is available, the exporter
accepts its `transcript.log` and `task-prompt.txt`; it marks the omitted Squid
log unavailable. `--raw-inventory` accepts a separately reviewed JSON inventory
with an `edges` array. Preserve the original sensor log separately with its
source run ID and checksum. Do not use an inventory to infer a missing proxy
join.

Retrieve each artifact's API descriptor with
`gh api repos/jadoont/agent-behavior-index/actions/artifacts/ARTIFACT_ID`.
The optional descriptors connect an archive to its GitHub run and SHA, and
verify that the downloaded ZIP matches GitHub's SHA-256 digest when available.
If supplying an evidence ZIP, the exporter checks any separate `result.json`
against its archived copy and uses its captured self-report file. Implementation
checksums make the conversion reproducible even from a working checkout.

The exporter has no upload mode and always writes `PRIVATE_REVIEW_REQUIRED`.
Review **every** prompt, tool input/output, reasoning block, path, name,
credential and source SHA; pattern-based redaction is not sufficient for
public release. Document removals and unresolved gaps. Confirm the 199-trace
prototype's unit of analysis and provenance before combining it with these
run-level records. Report \(n\) per cell and use matched controls once the
three new controls exist. Keep the archived C0/T2 pilots in a separate cohort;
do not count them among the newly approved three controls.

Format reference: <https://huggingface.co/docs/hub/session-traces-format>.
