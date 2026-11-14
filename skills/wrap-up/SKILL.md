---
name: wrap-up
description: "The last phase of a wave: validate what the workers reported, ask the operator before merging anything, then recap and recommend the next step. Use when a wave drains, when workers report READY_FOR_INTEGRATOR, or when the operator asks what is next."
---

# Wrap-up

Run by the parent session, never by a worker. Nothing here is scheduled. It puts `fanout`, `cross-review`,
`evidence` and `full-send` in order at the end of a wave and adds the checks below. `fanout`'s final table is the
log; the recap in step 4 is what the operator reads.

1. **Collect** the wave's candidates by status word, from `fanout/scripts/wave-status` and the open PRs.
   Start from what the wave launched, not from what reported (the worktrees, the `delegate` rows of the
   trail, the delegated threads): each worker is done, replaced or absorbed into another's scope, and one
   that never reported is a finding, not an absence. A
   `READY_FOR_INTEGRATOR` row whose PR is already merged or closed is old: ignore it. A report is not evidence:
   read the real artifact (the PR or branch, the head SHA, the checks). When the description, the bot summary and
   the code disagree, the code at the head and the checks win. For an `INTEGRATED` report, confirm the merge
   commit is on the integration branch (`git merge-base --is-ancestor`) and nothing more.
2. **Validate each `READY_FOR_INTEGRATOR` candidate** once, in its own worktree or in a detached scratch
   worktree. `git rev-parse HEAD` must equal the PR head and the tree must be clean. Run one gate at a time with a
   time limit. A local service without credentials is fine; anything that needs live services or secrets is not
   run, and you say so.
   - Scope: `git diff` against `git merge-base HEAD origin/<integration branch>` stays inside the ticket's
     `Touches:`. `RUNSTATE.md` and `.artifacts/` are exempt; list every other file outside it and decide.
   - Proof: `evidence/scripts/proof-valid --base origin/<integration branch>` against the checklist or patch id in
     the PR description. When the ticket names where it must work, run it with `--checklist <file> --surface <name>`:
     a candidate proven only somewhere else goes back, or you prove it there yourself. It is not passed on to the
     operator to try. A checklist with an empty `Patch-id:`, or none, is "proof without anchor": rely on your own
     rerun. Rerun the gate the ticket's `Done when:` names, focused.
   - Screens: for a change to `ui_paths` files, run `evidence/scripts/pr-evidence-check --pr <number>`. A PR that
     shows no screenshot goes back; do not take the images from `.artifacts/` on the worker's word.
   - Criteria: mark each one met, not met, or pending the operator. A criterion the worker rewrote is a decision
     for the operator, never met.
   - CI: a job that never ran is neither a pass nor a failure (`babysit-pr`, "When CI is red"): say "CI did not
     run" and rest on your rerun. A failure at the head is a failure.
   - Review: when a change is on `cross-review`'s high-risk list, or user-visible under `verify_mode`, and no
     verdict in the PR description covers this patch, run `cross-review` yourself in the mode it names. A
     verify-mode verdict covers it while `proof-valid --patch-id` accepts its patch id; a break-mode verdict covers
     the head it names.
   - Write down what the worker said it did not verify and what you did not check.
3. **Decide each one**, before anything is merged.
   - Send it back with the failing criterion, to one fresh worker with the whole brief (the original brief,
     every later decision, the previous report and the branch), per `fanout` step 4. Message the old worker
     only when what the fix needs lives in it and is costly to move (its checkout, uncommitted changes, a
     running process): a message restarts an idle agent, and a chain of resumes drops instructions. Write the
     send-back in the ticket's comment; a ticket whose comments show two send-backs goes into the question
     instead.
   - Leave it READY with the reason.
   - Offer to merge only when every criterion is met and the Merge gate of `full-send` is green on the head.
     Merging is the operator's call: it goes in the question as an option that names the PR and its head, and says
     when the change deploys or migrates on merge. Never merge what you could not validate.
   - `WAITING` goes back to `fanout`; `BLOCKED(decision)` goes into the question.
4. **Recap, then recommend.** Line one: what changed for the user, or what the operator must decide. At most
   three bullets: what entered (PR links), what is blocked and what unblocks it, what is not verified. No hashes
   or thread ids. Then the next step: with one candidate left, the action that unblocks it; otherwise what this
   wave unblocked and the read-only part of `groom` (steps 1 to 4). ONE recommendation and up to two
   alternatives, each with what changes for the user, why now, and its risk or dependency; independent tickets
   may go together. Put every decision the operator owes in ONE question, the recommended option first, asked
   with the "Ask the user" action in `jstack`, in the operator's language. Never "nothing to do, what do you
   want?".
5. **Act on the answer, then record.** Merge only the PRs the yes names, and only while the head is still the one
   it named: fetch first, rebase when `babysit-pr` says to, merge as `full-send` says, then run `fanout`'s full
   build on the integration branch again and report the result; a red build does not undo the merge. Then record
   in the tracker, which only adds and never cancels, folds or parks: one comment per ticket with the verdict, the
   PR link and the proof summary (the artifacts stay in the worktree's `.artifacts/`); follow-up tickets for the
   out-of-scope risks the workers declared (search the open tickets first). Nothing moves to done but the
   operator's acceptance: integrated work goes to review. The decisions the operator gave go to the product doc.
   Remove the worktrees and branches this session created or merged once the comment holds the proof summary; a
   worker's own are `ticket-start`'s.
