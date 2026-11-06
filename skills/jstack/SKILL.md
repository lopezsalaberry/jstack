---
name: jstack
description: "Reference for the settings, harness actions, status words and RUNSTATE.md that every other skill in this stack uses. Read it when a skill names a setting (like `models` or `quota_probe`) or an action (like 'delegate' or 'watch the PR'), or to check that the stack is installed."
---

# jstack core

The other skills say what to do in terms of **settings** and **actions**. This skill
defines both, so nothing else has to be installed.

Requires `git`, `gh` (authenticated) and `python3`. Check with
`scripts/doctor` (or `./install.sh --doctor`): it names what is missing.

## Settings

Put them in the repo's `AGENTS.md` under a heading `## jstack settings`, one
`key: value` per line. Read the resolved values with `scripts/jstack-settings [key]`.
Precedence: environment `JSTACK_<KEY>` over `AGENTS.md` over the default.

| Key | Default | Meaning |
|---|---|---|
| `integration_branch` | the remote's default branch | Where green tickets merge |
| `models` | empty | Ordered `provider:model` list for workers. Empty: use the model the harness already runs, no switching |
| `reviewer_models` | `auto` | Ordered preference for `cross-review`: entries are `provider:model` or `auto` (any model the harness can start, other families first). Example: `provider-a:model-x, auto` means prefer that model, otherwise whatever is available |
| `quota_probe` | the probe shipped with `quota-gate` | Command that answers whether a provider has quota. Contract in `quota-gate` |
| `quota_source` | `.jstack/quota.txt` | File the shipped probe reads |
| `quota_max_age_minutes` | `30` | Older data counts as unknown |
| `iteration_minutes` | `60` | Longest an iteration may run without the metric moving (see `iterate`) |
| `max_parallel` | empty | Optional cap on workers at once. Empty: limited by quota only |
| `review_bots` | empty | Comma list of review-bot logins whose review `babysit-pr` waits for. Empty: none |
| `advisory_bots` | empty | Review bots that are reported but never waited for |
| `verify_mode` | `visible` | When `cross-review` runs in verify mode: `off`, `visible` (user-visible changes only) or `always` |
| `ui_paths` | empty | Comma list of globs (for example `src/ui/**, **/*.css`) that mark a change as UI. Empty: the design gate is off |
| `design_tokens` | `design/tokens.json` | The design system's tokens, the source `token-lint` checks against |
| `design_check` | empty | Command that must exit 0 on a UI change, run from the repo root. Empty: the shipped `full-send/scripts/token-lint` with `design_tokens` and `ui_paths`. Set it to also run your design file's own lint or a visual comparison |
| `posthoc_queue` | empty | File where `cross-review` queues unproven findings. Empty: put them in the PR |
| `paid_fallback` | `off` | `off`, or `<provider> <daily cap>` to allow pay-per-token work after subscriptions run out |

## Actions

Skills name an action; use the harness's tool for it, or the fallback. The fallback
needs only `git`, `gh` and `python3`.

| Action | Claude Code | T3 Code | Codex | Fallback |
|---|---|---|---|---|
| Delegate a task to another agent | `Agent` tool | `delegate_task` | `spawn_agent` | Start a fresh session of the other CLI with the brief as its prompt, in its own worktree |
| Watch a PR until something changes | `pr-wait` under the `Monitor` tool | `watch_pull_request` | `pr-wait` as one long command | `babysit-pr/scripts/pr-wait` as one long command |
| Ask the user | `AskUserQuestion` | the question tool | `request_user_input` | Stop with `BLOCKED(decision)` and put the question first in the final message |
| Wait for a background command | `Monitor` | `t3_background_wait` | wait in the foreground | Run it in the foreground with a timeout |
| List the models and providers you can start | the `/model` menu | `orchestrator_capabilities` | the model picker | Try the entries of the list in order: a refusal for quota, authentication or availability is the answer |

Never use two watchers on one PR. A delegated child never watches a PR its parent owns.

## Status words

Every worker ends with one of `INTEGRATED <sha>`, `READY_FOR_INTEGRATOR`,
`WAITING <resume condition>`, `BLOCKED(env|task|decision) <reason + evidence>`.
`iterate` says when each applies.

## RUNSTATE.md

One file per ticket, at the worktree root, rewritten at every verdict and pushed as a
WIP commit. A fresh worker continues from it. These header lines are read by
`fanout/scripts/wave-status`:

```
Status: WORKING | WAITING <condition> | BLOCKED(<type>) | INTEGRATED <sha> | READY_FOR_INTEGRATOR
Done when: <one observable predicate>
Metric: <name>
Baseline: <number>
Now: <number>
Next step: <one sentence>
```

Below the header: what was tried (hypothesis, change, verdict), what is known, and the
premises tested.

For work nobody is watching, also keep `TRAIL.tsv` next to it: one append-only row per decision
(`scripts/trail TRAIL.tsv <phase> <decision> <why> <evidence> <result>`). Evidence is a pointer
(SHA, PR, `file:line`, artifact path). A wrong call is superseded by a new row, never edited.
`scripts/trail --check` validates the file.
