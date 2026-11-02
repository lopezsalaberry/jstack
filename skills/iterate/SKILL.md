---
name: iterate
description: "How a worker keeps going until the ticket's predicate is true: a measured loop with no attempt cap. Use whenever a gate, check or review finding fails, and before you stop, hand off or report BLOCKED."
---

> New in jstack. Adapted from [pstack](https://github.com/backnotprop/pstack) `figure-it-out` (hypothesis loop, verdicts), `principle-attack-the-premise` and `principle-never-block-on-the-human`; and from [tstack](https://github.com/t3dotgg/tstack) `full-send` ("ask only when you cannot continue alone", smallest change) and `babysit-pr` (keep the PR at the size the goal needs). tstack has no attempt cap; jstack's old "3 fix attempts" cap was our own addition and cut real work short (2026-11-02: a worker stopped after four minutes with the branch still moving).

# Iterate

**A count of attempts is never a reason to stop. Progress is.** Two failures that share a premise are a reason to change the premise, not to quit.

## Before the first change

Write these in `RUNSTATE.md` (create it if missing), with the baseline taken from the pre-change state:

- **Done when:** one observable, falsifiable predicate.
- **Progress metric:** the number that must move, for example failing checks, failing tests, unresolved findings. Record baseline and current value.

## The loop: every unit is an experiment

1. **Hypothesis:** one sentence on the cause.
2. **Smallest change** that tests it. Fix the case that happened, not every case that could.
3. **Measure** on the real artifact, the gate that failed. Never a self-report.
4. **Verdict:**
   - `VERIFIED`: the metric moved toward the predicate or the check is green. WIP commit and update `RUNSTATE.md`.
   - `NOT VERIFIED`: revert the change and record what it ruled out.
   - `INCONCLUSIVE`: fix the measurement first. Inconclusive is not a pass and not a failure.

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
3. Report `WAITING` with the resume condition "continue from `RUNSTATE.md` at the WIP commit". The parent relaunches a fresh worker from it. Never report `BLOCKED` for a budget.

## Stop only when

- Progress **plateaus after a pivot**: the metric did not move across two consecutive pivoted approaches.
- The next step is **irreversible or outside the grant** (production, data deletion, outbound messages, closing a PR, force-pushing another branch).
- You **cannot prove** the change.
- The goal is **ambiguous** in a way that changes the result.
- **Another PR makes this one obsolete.**
- Two reviewers still disagree after two rounds: show both positions.

Then report a typed `BLOCKED(env)`, `BLOCKED(task)` or `BLOCKED(decision)` with the failing check, the premises you tested, the evidence, and what is needed. The queue moves on to the next ticket.

## Report

`INTEGRATED <sha>`, `READY_FOR_INTEGRATOR`, `WAITING <resume condition>` or `BLOCKED(<type>) <reason + evidence>`, always with: the progress metric from baseline to now, how many iterations ran (a count, never a cap), and the premises you tested.
