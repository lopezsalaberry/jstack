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
3. **Launch** one background worker per ticket with the default model (Sonnet;
   Opus only for design, design tools, or when the operator asks), using the harness's subagent or thread tool.
   Each worker runs `ticket-start` once, then `full-send`.
4. **Drain.** As workers report, launch the next ticket. Escalate `BLOCKED`
   tickets to the operator in one consolidated message.
5. **Stop** when no worker is running and every remaining ticket is blocked
   or waits on a blocked one. After the wave drains, run the full build once on
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
- Do not fan out. Stop after 3 fix attempts.

Report one of `INTEGRATED <sha>` or `BLOCKED <reason + evidence>`, with gate
results.

## Final report

Table: ticket, status, sha or blocker, fix attempts used. Then the day's
integrated merges: `git fetch origin && git log --first-parent --since=1.day origin/<integration branch> --oneline | wc -l`.
