# ABI gh-aw pilot

This branch adds a manually dispatched, non-publishing pilot for the committed
Claude, Codex and Gemini arms. It does not change the preregistered metrics or
establish a baseline from a single replicate.

## Run

```sh
gh workflow run record.yml --repo jadoont/agent-behavior-index \
  --ref main -f agent=claude -f task=c0
```

Use `task=t2` only after the control demonstrates working authentication and
workload evidence. Engines run serially. Each gets only its own inference secret.
Garnet uses OIDC, not a repository token. No credentials are committed.

Codex fails before inference unless `ABI_OPENAI_ORG_VERIFIED=garnet` is set as a
repository variable. Set it only after replacing `OPENAI_API_KEY` with a verified
key from Garnet's `abi-sprint` project. This is an operator attestation, not an
automatic account lookup.

## Bounds and evidence

### Model policy

Default to explicitly pinned, cost-effective models, with no automatic premium
upgrade. Claude uses `claude-sonnet-4-6`; the paused Codex arm is configured for
`gpt-5.6-terra`, and the paused Gemini arm for `gemini-3.8-flash`.
OpenAI describes Terra as balanced for everyday coding and tool use
(https://developers.openai.com/codex/models); Google describes Flash as
cost-efficient for autonomous agents and software engineering
(https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash).

Each engine has an exact provider/model allowlist. Model fallback and token
steering are disabled, so an unavailable model fails rather than silently
upgrading to Fable, Astra, Opus, Pro, or another model. The threat detector is
explicitly pinned to the same model with a separate 10 AI-credit, 3-turn bound.
Premium-model exceptions require explicit approval and a reviewed configuration
change. Codex and Gemini remain unverified until their account prerequisites are
resolved; configuration is not a claim of successful inference.

Compile with `python scripts/compile_ghaw.py`. gh-aw v0.88.8 does not propagate
the model allowlist/fallback controls to its separate detector, so this wrapper
also enforces them in both generated AWF JSON configurations. It fails if the
expected two configurations per workflow are not found. Do not bypass the wrapper.

### Execution bounds

- gh-aw compiler v0.88.8 with pinned actions and containers.
- Per-agent 12-minute execution timeout, 20-turn configured bound, 50 AI-credit
  proxy bound, and 100 AI-credit daily workflow guardrail. These are not provider
  dollar caps or key expiry controls.
- The same effective 45-domain allowlist across all three compiled agent steps.
- Docker/iptables runtime rather than a separate guest VM, so the host Garnet
  sensor can observe the workload. Actual edge coverage still needs inspection.
- Only a local completion handler and no-op outputs; failure issue creation is
  disabled. Agent repository access is read-only; `id-token: write` is granted
  for Garnet authentication and excluded from the agent sandbox. Only gh-aw's conclusion job receives
  `actions: write` to maintain its daily-usage cache; no job receives issue,
  pull-request or repository-content write permission.
- Redacted pilot artifacts retained seven days, plus standard gh-aw artifacts.
- An evaluator copied before agent execution checks task outcome, self-report,
  protected tracked-file changes and sensor presence. It is a pilot gate, not
  proof that the agent cannot tamper with the environment.
- T2's original shell check accepts its unchanged starter. The pilot instead
  requires `n=8 min=1 max=9 mean=3.88`.

The API proxy and kernel logs must be reviewed together before asserting network
attribution. A nonempty sensor file or a green job alone does not prove coverage.
The post-install canary is a benign unauthenticated GET to `api.github.com/zen`;
it does not read files, environment variables or credentials.

## Setup prerequisites

Provider-side project name: `abi-sprint`. Intended expiry: 30 days after creation.
Enforced spending caps and expiries must be verified at each provider separately;
the workflow does not create or enforce those account settings.

Claude billing is enabled for the `abi-sprint` workspace in Garnet labs. The
workspace limit is $50/month, auto-reload is off, and the September 22 key expires
October 22, 2026. Only the explicitly approved $25 credit purchase was made.
The repository's `ANTHROPIC_API_KEY` is an encrypted Actions secret, not a file.
OpenAI access was limited to the Personal organization, and Gemini project
creation was rejected by Google's anti-abuse check. Both arms remain paused;
do not interpret their committed configuration as successful validation.

The raw parser now retains gh-aw's container-rooted `awf-cmd-*.sh` workload
subtree while excluding sibling harness containers. This post-live correction
is recorded in `PLAN.md`; earlier outputs require reprocessing. The
`scripts/summarize_pilot.py` diagnostic inventories all raw chains without
pretending that a shared proxy connection identifies a particular client.

## Garnet candidate and Dependabot

The user-requested quickstart pins the UNACCEPTED v2.3.0 candidate
`249153cfd535f8a08c328c1ef71eeb4b1b9ac096`, with sensor `v2.17.0`:
https://garnetlabs-devin-1787188255-docs-v6-10-alignment.mintlify.site/quickstart

The pilot and standard `test.yml` both omit `api_token` and request
`id-token: write`. The standard test workflow records before checkout and
dependency installation, and handles every pull request, including Dependabot.
It does not use `pull_request_target`, expose provider keys, or spend AI credits.
The gh-aw workload capture starts at its pre-agent step, after host preparation.

Dependabot coverage becomes active for future PRs once these workflow changes
are merged. A real Dependabot-authored run is required to verify its OIDC behavior;
a human PR or manual run is not equivalent. No Dependabot account secrets are
required by this configuration, and missing recording must not be reported as a
successful empty profile.
