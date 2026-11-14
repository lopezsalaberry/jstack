---
name: jstack
description: "Reference for the settings, harness actions, status words and RUNSTATE.md that the other skills of this stack use. Read it when a skill names a setting (like `ui_paths` or `reviewer_models`) or an action (like 'delegate' or 'watch the PR'), or to check that the stack is installed."
---

# jstack

Five skills: `ticket` (one change, from the first edit to the merged PR), `review` (one round by someone who did not
write it), `wave` (several tickets at once, and what is next), `groom` (the backlog, by hand) and this reference.
Requires `git`, `gh` (authenticated) and `python3`. `scripts/doctor` (or `./install.sh --doctor`) names what is
missing.

## The rules card

The rules every session must follow are one short block, the card at the top of `templates/AGENTS.md`. An agent
follows a rule only if it reads it, and a skill is read only when it is loaded, so the card has to sit in a file the
harness always loads. `./install.sh --card <file>` writes it, and replaces an older one, in a repo's `AGENTS.md` or in
the file your harness loads for every repo (one copy there serves every repo on the machine). `doctor` says when
no such file has the current card.

## Settings

A repo's own values go in its `AGENTS.md` under a heading `## jstack settings`, one `key: value` per line. The
operator's own (which reviewers to prefer, which models to suggest) go in `~/.config/jstack/settings`, the same
lines, for every repo on the machine. `scripts/jstack-settings [key]` prints what was resolved. Precedence:
environment `JSTACK_<KEY>`, then the repo, then the operator's file, then the default.

| Key | Default | Meaning |
|---|---|---|
| `integration_branch` | the remote's default branch | Where green tickets merge |
| `ui_paths` | empty | Comma list of globs (`src/ui/**, **/*.css`) that mark a change as UI. Empty: the design gate is off |
| `design_tokens` | `design/tokens.json` | The design system's tokens, which the shipped token-lint checks against |
| `design_check` | empty | Command that must exit 0 on a UI change, run from the repo root. Empty: the shipped token-lint |
| `verify_mode` | `visible` | When `review` runs in verify mode: `off`, `visible` (user-visible changes) or `always` |
| `reviewer_models` | `auto` | Ordered preference for `review`: `provider:model`, a bare `provider`, or `auto` (anything the harness can start, other families first). `provider-a, provider-b, auto` means the first that has quota, then a fresh session of whatever is left |
| `routing` | empty | Free text the orchestrator reads when it picks a model for a ticket: what to prefer for which kind of work. A suggestion, not a rule |
| `max_parallel` | empty | Cap on workers at once. Empty: quota alone limits |
| `quota_probe` | the probe shipped with `wave` | A command that answers `--provider <name>` with exit 0 (has quota), 1 (none) or 2 (no data). Callers always run `wave`'s `scripts/quota-probe`, which keeps the refusal marks and asks this command for the reading |

## Actions

Skills name an action; use your harness's tool for it, or the fallback, which needs only `git`, `gh` and `python3`.

| Action | Claude Code | T3 Code | Codex | Fallback |
|---|---|---|---|---|
| Delegate a task to another agent | `Agent` tool | `delegate_task` | `spawn_agent` | A fresh session of the other CLI with the brief as its prompt, in its own worktree |
| Watch a PR until something changes | `pr-wait` under the `Monitor` tool | `watch_pull_request` | `pr-wait` as one long command | `pr-wait` as one long command |
| Ask the user | `AskUserQuestion` | the question tool | `request_user_input` | Stop with `BLOCKED(decision)` and put the question first in the final message |
| Check that a started agent answered | the result of the foreground `Agent` call | `t3_thread_wait` with a 2-minute timeout, then `t3_thread_read` | wait for it with a 2-minute timeout | Read the child's output after 2 minutes |
| List the models and providers you can start | the `/model` menu | `orchestrator_capabilities` | the model picker | Try `reviewer_models` in order: a refusal is the answer |

`pr-wait` ships with the `babysit-pr` skill in `extras/` (`./install.sh --extras`). Never use two watchers on one
PR. A delegated child never watches a PR its parent owns, and every delegate is told its model and effort.

## Status words

Every worker ends with one of `INTEGRATED <sha>`, `READY_FOR_INTEGRATOR`, `WAITING <condition>` (a budget ran
out; the condition is something observable, never "later") or `BLOCKED(env|task|decision) <reason and evidence>`.

## RUNSTATE.md

Written at the worktree root when a worker stops before the end (`WAITING` or `BLOCKED`), and pushed in a WIP commit,
so a fresh worker can continue. `wave`'s `scripts/wave-status` reads these header lines from every worktree:

```
Status: WAITING <condition> | BLOCKED(<type>) | READY_FOR_INTEGRATOR | INTEGRATED <sha>
Done when: <one observable condition>
Next step: <one sentence>
```

Below them: what was tried (idea, change, result) and what is known.
