# How gh-aw is wired here

Checked September 22, 2026 after the setup merge. The Claude run used real gh-aw
execution, but this is a custom experiment runner around gh-aw, not its complete
out-of-the-box PR automation experience.

## What runs

1. A human opens an experiment PR. It must be ready, trusted, from a branch in
   this repository, and labeled `abi:run`.
2. `experiment-pr.yml` checks the experiment JSON and calls `abi-claude.lock.yml`.
3. That lock file is generated from `abi-claude.md` and its shared import by gh-aw
   v0.88.8. gh-aw prepares the prompt, starts Claude inside its controlled
   container, records tool activity, and runs a separate threat detector.
4. Garnet observes process and network activity during the agent workload.
5. Our independent task checks inspect the output. A separate, non-agent Python
   step posts the checks and exact Garnet link to the PR.

Using an ordinary trigger workflow to call a compiled workflow through
`workflow_call` is a documented gh-aw pattern, not a substitute for running the
agent ([gh-aw glossary](https://github.github.com/gh-aw/reference/glossary/)).
The PR comment is our deterministic report, not a native `add-comment` safe
output.

## Proof beyond a green badge

The [verified run](https://github.com/jadoont/agent-behavior-index/actions/runs/35800450042)
contains native gh-aw activation, agent, detection, safe-output and usage artifacts.
The agent artifact's `agent_usage.json` records model `claude-sonnet-4-6`,
3,740 input tokens, 1,764 output tokens, cache use and 33.95253 AI credits for
the main agent. That last number is not dollars and excludes the separate detector.

The native `safeoutputs.jsonl` contains a real `noop` completion call describing
the median fix and three passing tests. The independently checked task result
and [posted receipt](https://github.com/jadoont/agent-behavior-index/pull/4#issuecomment-5786652151)
confirm the functional outcome. The detector artifact contains a completed
verdict, rather than an inferred result from job status.

Recompiling with `python scripts/compile_ghaw.py` produced no changes to the
checked-in lock files. The wrapper applies a narrow model-policy correction to
both generated proxy configurations; plain `gh aw compile` alone is not the
documented maintenance command for this repository.

## Why it may not look like gh-aw

- **Workflow list:** Runs appear under **ABI experiment PR**, the caller.
  `gh aw status` currently lists the three compiled workers as active but shows
  run ID `0` for each. That view is not a reliable run history for this setup.
  “Active” also does not mean Codex or Gemini credentials have been verified.
- **No conversational bot:** Writing a PR comment does not instruct the agent
  to make another change. There is no slash-command or comment-reply trigger.
- **No automatic code push:** The task is an experiment in a disposable checkout.
  Agent edits remain in `agent.diff`; they are not pushed to the experiment PR.
- **Custom receipt:** The result table is posted by `scripts/experiment_pr.py`.
  gh-aw's configured safe output is `noop`, not `add-comment` or
  `push-to-pull-request-branch`. Those are separate features that must be
  explicitly enabled ([safe-output documentation](https://github.github.com/gh-aw/reference/safe-outputs/)).

For now, open the PR's Checks and comments or use:

```sh
gh run list --repo jadoont/agent-behavior-index --workflow experiment-pr.yml
gh run view 35800450042 --repo jadoont/agent-behavior-index
```

## Limits of this review

- **Native audit output was incomplete:** In this environment, `gh aw audit`
  retrieved job metadata but did not retrieve the native agent artifacts. It
  printed zero turns and zero usage. Those zeros are missing data, not evidence
  of a free or empty run. Direct artifact downloads supplied the usage evidence
  above.
- **Static lint is not a clean pass:** `gh aw lint` could not invoke Docker here.
  Standalone actionlint 1.7.12 rejected generated `queue` and `job.workflow_*`
  fields, even though GitHub accepted and executed this exact configuration.
  Compilation, local tests and live execution passed; a fully compatible static
  lint pass is not claimed.
- **Daily budget is a start-time guard, not a dollar cap:** The verified
  activation log checked earlier run usage at 53.819835 of the configured 100
  AI-credit threshold and allowed the run. This verifies that check occurred,
  not a hard cap across all providers, callers or overlapping jobs. The provider
  workspace limit and per-run bounds remain separate controls.
- **Garnet step names:** The reusable workflow caused degraded step attribution.
  Process and network records were present, but some step names were unknown.
- **Scope:** Claude C0 is verified. T2 skipped installation. Codex and Gemini
  are not enabled, and a real Dependabot-authored OIDC run remains untested.

## What to review next

The first experiment can test the current runner without changing it. Keep that
PR in draft until the question and these limitations have been reviewed.

If the goal is normal gh-aw discoverability and PR interaction, the next setup
change should make the Claude Markdown workflow the direct PR entry point and
declare the desired native safe outputs. Test that change on its own PR rather
than quietly mixing it into the baseline experiment. The existing wrapper is a
supported execution pattern, but it should not be described as the complete
native gh-aw operating experience.
