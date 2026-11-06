---
name: iterate
description: "How a worker keeps going until the ticket's predicate is true: a measured loop with no attempt cap. Use when a gate or review finding fails twice, when a budget runs low, and before you stop, hand off or report BLOCKED."
---

# Iterate

**A count of attempts is never a reason to stop. Progress is.** Two failures that share a premise are a reason to change the premise, not to quit.

## Before the first change

Write these in `RUNSTATE.md` (create it if missing; its header lines are defined in `jstack`), with the baseline taken from the pre-change state:

- **Done when:** one observable, falsifiable predicate.
- **Progress metric:** the number that must move, for example failing checks, failing tests, unresolved findings. Record baseline and current value.

## The loop: every unit is an experiment

1. **Hypothesis:** one sentence on the cause.
2. **Smallest change** that tests it. Fix the case that happened, not every case that could.
3. **Measure** on the real artifact, the gate that failed. Never a self-report.
4. **Verdict:**
   - `VERIFIED`: the metric moved toward the predicate or the check is green.
   - `NOT VERIFIED`: revert the change and record what it ruled out.
   - `INCONCLUSIVE`: fix the measurement first. It is not a pass and not a failure. Two consecutive `INCONCLUSIVE` on the same measurement is `BLOCKED(env)`: the instrument is broken.

**Every verdict, VERIFIED or NOT VERIFIED, ends with `RUNSTATE.md` updated and pushed as a WIP commit**, so a worker that dies without reporting loses at most one iteration.

At the start of every iteration record `started_at` and the metric in `RUNSTATE.md`, check your context fill, and apply `quota-gate` to your own provider (exit 1: go to "Budgets", report `WAITING`).

**Per-iteration brake.** If an iteration runs the `iteration_minutes` setting (default 60) with no metric movement and no new verdict, close it as `INCONCLUSIVE`, write the state, and pivot or report `WAITING`. This brakes stagnation; it does not cap how many iterations a ticket may take.

## When it does not move

- **Look at the shape of the failures before the failures.** Hundreds of failures usually share one cause (an uninstalled dependency, a renamed export, a stale base, a missing fixture). Find what they have in common before touching any single one.
- **The same failure twice with the same premise: stop fixing.** Write the premise as one sentence in `RUNSTATE.md`, test it directly with an observation that would come out differently if it were false, then pivot the approach or the model.
- **Environment failures do not count.** A broken tool, sandbox, harness or missing dependency gets fixed, then the loop reruns.
- **Shrink instead of widening.** If the branch is far behind or the change keeps growing, land a smaller unit that is green and list the rest as follow-ups with a written reason. Do not grow the PR one cheap-looking fix at a time.
- **Reversible choices never block.** Decide, proceed, and list the decision in your report.

## Budgets are not failures

Quota, rate limits, time and context are budgets. When one is nearly used up, with progress made:

1. WIP commit and push.
2. Update `RUNSTATE.md`: what was tried (hypothesis, change, verdict), what is known, the metric before and now, and the next step.
3. Report `WAITING` with an **observable** resume condition: a `quota-gate` probe that passes, a timestamp, or "now" for time and context, always with "continue from `RUNSTATE.md` at `<sha>`". Never "later". The parent relaunches ONE fresh worker for the same ticket from it (see `fanout`). Never report `BLOCKED` for a budget.

## Stop only when

- Progress **plateaus**: the metric did not improve across two consecutive iterations that each tested a different premise, or across three consecutive iterations of any kind. This counts stagnation, not attempts: any improvement resets it.
- The next step is **irreversible or outside the grant** (production, data deletion, outbound messages, closing a PR, force-pushing another branch).
- You **cannot prove** the change.
- The goal is **ambiguous** in a way that changes the result.
- **Another PR makes this one obsolete.**
- Two reviewers still disagree after two rounds: show both positions.

Then report a typed `BLOCKED(env)`, `BLOCKED(task)` or `BLOCKED(decision)` with the failing check, the premises you tested, the evidence, and what is needed. `BLOCKED(decision)` is the question you would have asked, with the options and your recommendation first. The queue moves on to the next ticket.

## Report

`INTEGRATED <sha>`, `READY_FOR_INTEGRATOR`, `WAITING <resume condition>` or `BLOCKED(<type>) <reason + evidence>`, always with: the progress metric from baseline to now, how many iterations ran (a count, never a cap), and the premises you tested.
