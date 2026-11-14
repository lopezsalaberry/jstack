---
name: wave
description: "Run several tickets at once, one worker each, then validate what they report and tell the operator what is next. Use for 'run these tickets', 'fan out', a queue of independent work, when workers report back, or when the operator asks what is next."
---

# Wave

Run by the session the operator talks to. You run the program, not the code: you decide who does each ticket and
you check what comes back. The scripts named here are in this skill's `scripts/` folder.

## Queue

Ready tickets from the project's tracker, each with a goal, `Touches:` (the files it expects to change) and an
observable `Done when:`. Write a missing one from the code before launch. One worker per ticket and one level deep:
a worker starts no workers, only the reviewer of `review`. Tickets whose files overlap run one after the other;
a ticket with no `Touches:` runs alone. One ticket is a wave of one.

At the start of a session run `scripts/wave-status`, list the open PRs and relaunch what is `WAITING` before you
pick new work.

## Launch

1. **Quota.** `scripts/quota-probe --provider <provider>` before every launch. Exit 1: not that provider. Exit 0
   or 2: go; 2 means no data, which is not exhaustion, so write "quota unknown" and carry on. A reading from earlier
   in the session is not data.
2. **Model and effort.** You choose for each ticket, from what the harness can start (see `jstack`) and the
   operator's suggestions in `routing`; depart from a suggestion only with a reason you write down. Quota says
   which providers are available, never which model suits the work: do not move work around to even out usage.
   Effort starts from your session's level: one step up for the hardest work, one or two down for routine edits.
3. **Brief.** `scripts/brief <ticket> --goal … --done-when … --touches … --model … --effort …` prints the brief
   (`--surface <name>` when the ticket names a device, a browser or the packaged app).
   Start one background worker with it through the harness's delegate action, on that model and effort. A
   delegate that is not told its model inherits yours. `max_parallel` caps how many run; otherwise quota does.
4. **A refusal is data.** If the start fails for quota, rate limit, authentication or availability, or shows
   nothing in 2 minutes, run `scripts/quota-probe --mark-exhausted <provider>` (`--until <date>` when the refusal
   names when it comes back) and relaunch the ticket at once on the next provider that passes. On HTTP 429 halve
   the number running and climb back one at a time.
5. **The only wait.** When nothing can start, the ticket is `WAITING` until a probe passes. Never fail a ticket for
   quota. Pay-per-token routes are used only when the operator asks for them for that task.

## While it runs

Launch the next ticket as each worker reports. `WAITING <condition>` is parked, not done: when the condition holds,
start ONE fresh worker from the WIP commit and `RUNSTATE.md`, with a new brief (`--note "continue from RUNSTATE.md
at <sha>"`). A worker whose branch has not moved for an hour and that has not reported is treated the same way.
New work for a ticket goes to a fresh worker with the whole brief (the original, every later decision, the last
report, the branch). Message an old worker only when what the work needs lives in it, such as its checkout or a
process it runs. `BLOCKED` tickets go to the operator together, in one message.

## When it drains

Yours to do, never a worker's.

1. **Account for everyone.** Each worker you launched is done, replaced or absorbed into another. One that never
   reported is a finding, not an absence.
2. **Validate.** A report is not evidence. For each `READY_FOR_INTEGRATOR`, in its worktree at the PR's head, run
   `ticket`'s `scripts/check <ticket> --pr <number>` yourself (add `--surface <name>` when the ticket names where it
   must work) and rerun the check that `Done when:` names. The diff
   stays inside `Touches:`; list every file outside. A criterion the worker rewrote is the operator's decision,
   never met. A high-risk or user-visible change with no `Review:` line for this patch gets `review`, run by you.
   For `INTEGRATED`, confirm the merge commit is on the integration branch. Write down what nobody verified.
3. **Decide each one.** Send it back to a fresh worker with the failing line of `check` (a ticket sent back twice
   goes into the question instead), leave it ready with the reason, or offer to merge it. Merging what a worker
   left ready is the operator's call unless they already said to merge green tickets. Never merge what you could
   not validate.
4. **Build once.** Run the full build on `origin/<integration branch>` and report it. A red build does not undo a
   merge.
5. **Recap, then recommend.** First line: what changed for the user, or what the operator must decide. At most
   three bullets: what entered (PR links), what is blocked and what unblocks it, what is not verified. No hashes.
   Then ONE recommendation and up to two alternatives, each with what changes for the user, why now, and its risk.
   Every decision the operator owes goes in ONE question, the recommended option first, in their language, asked
   with the harness's question tool. Never "nothing to do, what do you want?".
6. **Record after the answer.** Merge only the PRs the yes names, while their head is the one it named. In the
   tracker: one comment per ticket with the verdict, the PR and the proof; user-visible work goes to review, not
   done, until the operator accepts; a follow-up ticket for each risk a worker declared out of scope. A decision
   the operator gave goes to the project's product doc, the one place decisions live. Remove the worktrees and
   branches you created.

End with a table: ticket, status, PR or blocker, model.
