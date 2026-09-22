# Garnet onboarding and verification

This repository already records its GitHub Actions jobs with Garnet. The
`test` workflow runs the analysis tests under the sensor; `Record agent run`
is a separate, manually dispatched research workflow.

## Prerequisites

- A GitHub-hosted `ubuntu-latest` job.
- A repository secret named `GARNET_API_TOKEN`, created through Garnet's
  dashboard under Settings → API Tokens. Do not put the token in a file or PR.
- The workflow permissions `contents: read` and `pull-requests: write`.
- Follow the [current quick start](https://docs.garnet.ai/quickstart) for the
  Garnet Runtime Review GitHub App installation. The app installation and
  the Action's own comment fallback are distinct paths; check which one
  actually produced your evidence.

Both workflows pin `garnet-org/action` to
`3d47f4a9004f7356c980a0e8d420ef5984750e3c` (v2.2.0).
Check [the official pin](https://garnet.ai/pins) before upgrading.

## Verify your first pull request

1. Open a same-repository PR. The `test / analysis` job installs pytest and
   runs `python -m pytest -q analysis`. No model-provider key is needed.
2. Check that the Garnet step starts and its post-job step completes. A green
   test result alone does not establish that a runtime profile was captured.
3. Inspect the Garnet comment and Actions job summary. Record the comment
   author, full commit marker, workflow/run identity, and exact profile URL.
4. Compare the recorded commit with the PR head. GitHub's synthetic merge
   commit is a different identity: do not silently treat it as the head SHA.
5. Open the exact profile URL in a signed-out browser. A dashboard login page
   is not a public, independently readable Execution Profile.
6. Follow the [agent-consumption contract](https://docs.garnet.ai/consume).
   Missing, pending, stale, or incompatible evidence must be reported as
   unavailable for the current head, not as a clean execution.
7. Push a documentation-only follow-up commit. Confirm that the existing
   comment updates to the new commit and states what changed relative to the
   previous recorded run. A second comment is not evidence of an in-place
   update, and an unchanged workload does not guarantee identical network
   observations on ephemeral runners.

The Python dependency installation can legitimately reach PyPI and its
distribution infrastructure. Read the process ancestry and step attribution;
a hostname by itself is not a security verdict. Runner/DNS traffic must be
distinguished from workload traffic.

## Scope and rollback

The onboarding verification exercises the existing analysis CI, not the live
agent research matrix. It does not demonstrate filesystem capture, complete
execution coverage, or security of a dependency.

To stop recording, remove the Garnet step from each workflow. A repository
administrator can then remove the dedicated secret and revoke the token or
app access if they are no longer used. Retained evidence and deletion policy
must be checked with Garnet separately.
