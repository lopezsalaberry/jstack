---
name: fanout
description: "Run many independent tickets in parallel, one worker per distinct ticket, one level deep, limited only by model quota. Use for 'fan out', 'run these tickets in parallel', or a queue of independent work."
---

> Adapted from [backnotprop/pstack](https://github.com/backnotprop/pstack) `swarm` @ `25abb38559ddbabec563646224d09eff9a250eca` (upstream: cursor/plugins pstack). Races, best-of, and duplicate candidates removed.

# Fanout

## Rules

- One worker per distinct ticket. Never give two workers the same ticket.
- One level only. A worker never fans out and
  never starts reviewers other than `sol-loop` for high-risk work.
- No fixed worker count. `quota-gate` decides when to launch.

## Loop

1. **Queue.** Ready tickets from the project's tracker, with id, goal, and the
   files each expects to touch. One ticket is a queue of one.
   Tickets that touch the same files run one after the other, not in parallel.
2. **Gate.** Apply `quota-gate` before each launch.
3. **Launch** one background worker per ticket with the model `quota-gate` picks (Sonnet;
   Opus only for design, design tools, or when the operator asks; `gpt-6.1-sol` with handoff when Claude is at 0%), using the harness's subagent or thread tool.
   Each worker runs `ticket-start` once, then `full-send`.
4. **Drain.** As workers report, launch the next ticket. Escalate `BLOCKED`
   tickets to the operator in one consolidated message. `WAITING <condition>` is
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
- Do not fan out. Iterate with the `iterate` skill: there is no attempt cap. Stop only by its stop rules.
- A budget (quota, rate, time, context) is not a block: write `RUNSTATE.md`, push the WIP commit and report `WAITING` with an observable resume condition.
- `BLOCKED(decision)` is the question you would have asked, with the options and your recommendation first.
- `READY_FOR_INTEGRATOR`: the Merge gate is green and the PR is open but not merged because this repo's contract has a single integrator who merges.

Report one of `INTEGRATED <sha>`, `READY_FOR_INTEGRATOR`, `WAITING <resume condition>` or
`BLOCKED(env|task|decision) <reason + evidence>` (the status vocabulary of `iterate`), with gate results and the progress metric
(baseline to now).

## Final report

Table: ticket, status, sha or blocker, progress (baseline to now), iterations run. Then the day's
integrated merges: `git fetch origin && git log --first-parent --since=1.day origin/<integration branch> --oneline | wc -l`.
