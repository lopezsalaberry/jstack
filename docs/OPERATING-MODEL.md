# Operating model

How jstack behaves in practice. The skills hold the detailed rules; this page is the map.
Every rule here is enforced by a skill or a tool in this repo, not by anything outside it.

## Iteration policy (no fixed attempt cap)

The loop, the verdicts and the stop rules are in `skills/iterate/SKILL.md`. In short:

- **Fresh session per iteration.** Each iteration starts from the ticket's `RUNSTATE.md`
  (what was tried, what is known, next step), not from chat history.
- **WIP commit on progress.** Any iteration that moves the ticket forward ends with a WIP
  commit and an updated `RUNSTATE.md`.
- **Same failure twice means test the premise.** Write down the assumption behind the
  approach, test it directly, then pivot the approach or the model.
- **Environment failures do not count.** A broken tool, sandbox or harness is fixed; it
  never consumes the ticket's budget.
- **Limits are budget, not attempts.** Quota, rate limits or the per-iteration time limit
  (`iteration_minutes`). When a budget runs out the worker writes `RUNSTATE.md`, pushes a WIP
  commit and reports `WAITING` with an observable resume condition. `fanout` relaunches a
  fresh worker from it.
- **Stop only when** progress plateaus after a pivot, the next step is irreversible, or two
  reviewers still disagree after two rounds (show both positions to the owner).
- **Typed BLOCKED.** A stuck item reports `BLOCKED(env)`, `BLOCKED(task)` or
  `BLOCKED(decision)` and the queue moves on.

A test (`tests/test_policy.py`) fails if any skill, template or doc reintroduces a fixed
attempt cap, so the docs and the skills workers read cannot drift apart.

## Quota fallback order

`quota-gate` runs before every launch. Providers and models come from the `models` setting.

1. Walk `models` in order; the first provider with quota (or unknown quota) is used.
2. Moving to another provider is a hand-off through `RUNSTATE.md` plus a fresh brief, never a
   silent switch mid-thread. A harness that cannot move a running thread starts a new one.
3. Pay-per-token routes are off unless `paid_fallback` names a provider and a daily cap.
4. When every provider is at 0%: pause, commit, report `WAITING`, resume after the reset.
   Never fail a ticket for quota.

## Parallel batches

`fanout` runs several tickets at once when they do not touch the same files.

- **File set per ticket.** Each brief declares `Touches: path, dir/, glob/*.py`. No file set
  means the ticket is exclusive and runs alone.
- **Conflict groups.** Overlapping tickets run one after another; disjoint ones run together,
  each in its own worktree and branch with its own `RUNSTATE.md` and PR.
- **Cap.** Quota limits the wave; the optional `max_parallel` setting adds a cap.
- **Rate-limit backoff.** A provider 429 halves the number running and requeues the ticket;
  the number climbs back one step at a time.
- **Idempotent.** Finished tickets are skipped on relaunch; a `BLOCKED` ticket is retried and a
  `WAITING` one resumed from its `RUNSTATE.md`.

## Conventions the skills enforce

- **One worker thread per ticket.** A ticket never shares a worker; reruns reuse its thread.
- **Briefs carry a done-when state.** Every brief states the observable state that means done,
  so the worker and any reviewer judge the same thing.
- **Heartbeat from state, not from a model.** `skills/fanout/scripts/wave-status` reads the
  `RUNSTATE.md` of every worktree.
- **Clean up after integration.** The worker that integrated removes its worktree and branch
  (`ticket-start`).
