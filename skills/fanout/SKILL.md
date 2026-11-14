---
name: fanout
description: "Run many independent tickets in parallel, one worker per distinct ticket, one level deep, limited only by model quota. Use for 'fan out', 'run these tickets in parallel', or a queue of independent work."
---

# Fanout

## Rules

- One worker per distinct ticket. Never give two workers the same ticket.
- One level only. A worker never fans out and
  never starts reviewers other than `cross-review` for high-risk work.
- No fixed worker count. `quota-gate` decides when to launch. The optional
  `max_parallel` setting (see `jstack`) adds a cap; empty means quota alone limits.
- A provider rate-limit error (HTTP 429) halves the number of workers running at once and
  requeues that ticket. The number climbs back one at a time after a quiet period.

## Loop

1. **Queue.** Ready tickets from the project's tracker, with id, goal, and the
   files each expects to touch (`Touches: path, dir/, glob/*.py`). One ticket is a queue
   of one. Tickets whose file sets overlap run one after the other; disjoint ones run
   together, each in its own worktree and branch. A ticket with no declared file set is
   exclusive and runs alone.
2. **Gate.** Apply `quota-gate` before each launch.
3. **Launch** one background worker per ticket with the model and effort `quota-gate` picks, named in
   the delegate call, using the harness's way to delegate a task (see `jstack`). Each worker runs
   `ticket-start` once, then `full-send`.
4. **Drain.** As workers report, launch the next ticket. Escalate `BLOCKED`
   tickets to the operator in one consolidated message. A worker that stopped because its provider
   refused (quota, rate limit, authentication) is not parked: mark the provider as `quota-gate` says and
   relaunch ONE fresh worker for the same ticket at once on the next candidate, from its WIP commit and
   `RUNSTATE.md`. Park it only when no candidate can start. `WAITING <condition>` is
   parked, not done: when the condition holds (the `quota-gate` probe passes, a
   timestamp, or "now" for time and context) relaunch ONE fresh worker for the same
   ticket from its WIP commit and `RUNSTATE.md`, with a new brief that points to
   them. A worker that dies without reporting, with its branch no longer moving, is
   treated as `WAITING` from its last `RUNSTATE.md` push.
5. **Stop** when no worker is running and every remaining ticket is blocked,
   waits on a blocked one, or is `WAITING` on a condition that has not yet held. After the wave drains, run the full build once on
   `origin/<integration branch>` and report the result; it never blocks integration.

## Worker brief

Every brief stands alone and includes: ticket id, goal, expected files,
integration branch, the per-ticket gate (tests, lint, build, required CI), and these rules:

- **"full send": follow `full-send` end to end. You may merge this ticket's
  PR into the integration branch when its Merge gate passes.**
- **Do not ask the user anything. This overrides "Asking the user" in
  `full-send`. When you would ask, stop and report `BLOCKED` with evidence.**
- If the repo has no `verify-<app>` skill or no GitHub remote, report `BLOCKED`
  before editing.
- **When the ticket names where it must work** (a device, a browser, the packaged app), the brief names
  that surface and says: start with `checklist-init <ticket> --surface <name>` and prove it there
  (`evidence`, "Prove it where it has to work"). Proof elsewhere is a stand-in.
- **A UI ticket carries a Design block.** When the ticket's `Touches` match `ui_paths` (see
  `jstack`), the brief names the design sources (the `design_tokens` file and wherever the
  project keeps components and screens), says to read them before editing and to use only the
  tokens and components they define, and adds to its done-when: the design check is clean and
  every changed screen has a screenshot. If the design system lacks what the ticket needs, the
  worker reports `BLOCKED(decision)` naming the missing piece. Extending the design system is its
  own ticket and goes first.
- Do not fan out. Iterate with the `iterate` skill: there is no attempt cap. Stop only by its stop rules.
- A budget (quota, rate, time, context) is not a block: write `RUNSTATE.md`, push the WIP commit and report `WAITING` with an observable resume condition.
- `BLOCKED(decision)` is the question you would have asked, with the options and your recommendation first.
- `READY_FOR_INTEGRATOR`: the Merge gate is green and the PR is open but not merged because this repo's contract has a single integrator who merges.

Report one of `INTEGRATED <sha>`, `READY_FOR_INTEGRATOR`, `WAITING <resume condition>` or
`BLOCKED(env|task|decision) <reason + evidence>` (the status vocabulary of `iterate`), with gate results and the progress metric
(baseline to now).

## Watching a wave

`scripts/wave-status` lists every worktree of the repo that has a `RUNSTATE.md` with its
status, metric (baseline to now), next step and how long ago it was written. A worker
whose `RUNSTATE.md` has not moved for longer than `iteration_minutes` and whose branch has
no new commit is treated as dead, per step 4.

## Final report

Table: ticket, status, sha or blocker, progress (baseline to now), iterations run. Then the day's
integrated merges: `git fetch origin && git log --first-parent --since=1.day origin/<integration branch> --oneline | wc -l`.

When the wave drains, run `wrap-up` after this table: it validates what the workers reported and recommends the next step.
