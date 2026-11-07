# Operating model

The map of where each rule lives. The skills hold the rules; this page repeats none of them,
so there is nothing here that can disagree with a skill.

| Question | Where the rule is |
|---|---|
| How does a worker keep going, when does it stop, what counts as a budget? | `skills/iterate/SKILL.md` |
| Which model runs a worker, what happens at 0% quota, what is "unknown"? | `skills/quota-gate/SKILL.md` |
| How do tickets run in parallel, how are conflicts and 429s handled, who relaunches a stalled worker? | `skills/fanout/SKILL.md` |
| How is the backlog cleaned and ranked, and how is the next work chosen? | `skills/groom/SKILL.md` |
| How is a wave validated, closed and followed by a recommendation? | `skills/wrap-up/SKILL.md` |
| What do `INTEGRATED`, `READY_FOR_INTEGRATOR`, `WAITING` and `BLOCKED(...)` mean? | `skills/jstack/SKILL.md` (status words) and `skills/iterate/SKILL.md` (when each applies) |
| What goes in `RUNSTATE.md`? | `skills/jstack/SKILL.md` |
| What can a worker merge, force-push or delete? | `skills/full-send/SKILL.md` |
| When is a second model asked to review? | `skills/cross-review/SKILL.md` |
| Which settings exist and what do they default to? | `skills/jstack/SKILL.md` |

## Why there is no attempt cap

An early version stopped workers after a fixed number of fix attempts, and workers obeyed it,
quitting minutes into real work while the branch was still moving. Progress, not a count, is the
reason to stop. `tests/test_policy.py` fails if any skill, template or doc reintroduces a fixed
attempt cap, so the docs and the skills workers read cannot drift apart.

## Conventions the skills enforce

- One worker thread per ticket; reruns reuse its thread.
- Every brief states the observable state that means done.
- The wave's heartbeat is computed from state (`skills/fanout/scripts/wave-status`), not from a model.
- The worker that integrated removes its worktree and branch (`skills/ticket-start/SKILL.md`).
