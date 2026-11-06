---
name: full-send
description: Complete a ticket end to end autonomously: prove, PR, babysit, merge.
---

# Full Send

If the user triggered this, it's because they are not watching this thread, and
they want you to complete the work end-to-end autonomously. Your updates and
your final message go unread until long after you stop. You own the work from
its current state to a merged PR.

If the user did not explicitly request "full send" in some clear way, do not
assume full autonomy. If they did, everything below applies.

The user grants you permission to:

- Merge the PR once the merge gate passes.
- Force-push the PR's own branch with `--force-with-lease` after a rebase.
- Use the test methods that Proof needs, without asking first.

## Testing permission

A "full send" request is the permission. If a project file or other
instruction says to ask before a test method, or to leave testing to the
user, this request replaces that rule for this task.

That includes ask-first rules for computer use, browser automation,
simulators and devices, running the app or a dev server, screenshots, and
visual checks. Use the method that gives direct proof. List it in the
report.

Rules about how to test still apply. Follow rules that name the correct
command, fixture, or check. This permission only removes the ask-first or
leave-it-to-the-user step. If a preferred method cannot prove the change,
use a gated method under this permission.

It covers only the tests needed for this task. It does not add permission
for the steps under "Asking the user", such as production changes or data
deletion. It also does not bypass a harness or system approval prompt if
one appears.

## Steps

1. **Finish the change.** Complete the goal from the user's request with the
   smallest change that works. Fix the case that happened, not every case
   that could. Work in the ticket's worktree and branch from `ticket-start`.
2. **Prove it.** Get proof for every change you made. See "Proof".
   Open the app through the repo's `verify-<app>`, test what the ticket asks,
   and leave a pass/fail checklist (`evidence`).
3. **Get feedback.** Use `cross-review` in break mode (1 round) when the change touches a
   high-risk area listed there, and in verify mode when the change is user-visible and the
   `verify_mode` setting is not `off`. Otherwise skip cross-model review.
4. **File the PR** with the `file-pr` skill against the integration branch.
   Rebase onto the latest integration branch first. Paste the `evidence` checklist
   summary into the description, FAIL lines included.
5. **Babysit the PR** with the `babysit-pr` skill. Fix real findings and CI
   failures. Get proof for each fix before you push it. Keep going with the
   `iterate` skill while the checks move; there is no attempt cap. Report `BLOCKED`
   only by its stop rules, and `WAITING` when a budget runs out.
6. **Merge** into the integration branch when the Merge gate passes. Do not
   hold green tickets for a batch. The wave's full build runs separately and
   never blocks this.
7. **Report** in your final message, with the status vocabulary of `iterate` (`INTEGRATED`, `READY_FOR_INTEGRATOR`, `WAITING`, `BLOCKED(env|task|decision)`): the PR link, the merge commit, your proof,
   and each decision you made for the user.

Stay active from step 1 to step 7. If you end your turn while checks or bots are
pending, the work stops, because nobody will prompt you again. Wait with the
watcher from `babysit-pr`, so something wakes you when the PR changes. If you stop
before the merge, stop the watcher first.

## Stop before merge

If the operator asks to stop when the PR is ready, or the repo's contract names a single
integrator who merges, do steps 1 to 5 and skip step 6. The permission to merge above does
not apply. Leave the PR open and green, stop the watcher, and report `READY_FOR_INTEGRATOR`
with the PR link, the head SHA and the proof.

## Proof

Proof is evidence you observed yourself in this session: command output, a
reproduction, a screenshot. Use the most direct proof the change allows:

- Reproduce the original failure, apply the fix, then watch the same
  reproduction pass.
- Run the checks that the repo's CI runs (typecheck, lint, tests).
- Add one focused test that fails without the fix, when the behavior has none
  and the repo has a test setup.
- Before anything is delivered or published (a build, a package, a deploy),
  prove it on the artifact being delivered, the way a user gets it, not on a
  dev build. Use the project's `verify-<app>` skill
  (made with `create-verify`) and keep the evidence. No evidence, no publish.
- For a UI change (it touches `ui_paths`), the design gate is blocking. Run the `design_check`
  setting, or the shipped `scripts/token-lint` when it is empty: no new off-token color, size or
  font may land. Then capture a screenshot of every changed screen at the sizes the app supports
  and compare it with the design source, listing each mismatch. A tool can prove the tokens; it
  cannot prove a screen looks like the design, so an unresolved mismatch is `BLOCKED(decision)`
  with the screenshot beside the design, never a merge. Anything the design does not show (a new
  state or component) goes back to the design system first.
- For UI and runtime behavior, run the app and look at the change. Green mocked
  tests do not prove that the user experience works. Attach screenshots to the
  PR when they help and you have a way to upload them.

Grade each proof by the levels in `prove-it` ("How sure are you") and write the level next
to every `PASS`. Levels 1 to 3 are "unproven", not a pass. For a bug fix, keep the failing
output from before the fix and the passing output from after it, both verbatim, and commit the
failing test before the fix when the repo has a cheap test path for it.

When you cannot find a way to prove a change, you do not have full confidence.
Ask the user.

## Merge gate

Full confidence means all of these are true on the latest commit:

- Your proof covers every change in the diff, and `evidence/scripts/proof-valid` confirms it
  still describes the patch that will land (a rebase changes the commit, not the patch).
- A UI change has a clean design check and its screenshots attached.
- A user-visible change also has a verify-mode verdict of `PASS` or `PASS+NOTES` that covers
  this patch, unless `verify_mode` is `off`.
- The per-ticket gate (tests, lint, build for the touched scope, and the
  repo's required CI checks) is green.
- Review bots have finished, and each finding is fixed or dismissed with a
  written reason.
- No human review still requests changes.
- The branch is up to date with the integration branch, and GitHub reports it as
  mergeable.

### What blocks

Block a merge only for a problem you can show: a failing run at the head, a bug a user would
hit, a failed required gate, or documentation this PR made wrong. A problem the base already had
does not block unless the PR copies it or newly reaches it. Everything else (style, naming,
speculative edge cases, "might help") goes to a follow-up list with a written reason. A finding
nobody can reproduce is dropped, not queued.

Merge with the method the repo uses. Check the allowed methods and recent merged
PRs. If the repo uses a merge queue or auto-merge, stay until GitHub reports the
PR as merged. Merge through branch protection as configured. Never use `--admin`
or other bypasses. An automated review that only says "needs human review" and names
no concrete finding may be set aside when your proof covers the whole diff; say so in
the report. A review that names a finding is answered, never set aside.

## Asking the user

Under `fanout`, the worker brief overrides this section: never ask, report
`BLOCKED` with evidence instead.

A question in a normal message goes unseen, and the thread looks done. To ask
the user something, use the harness's question tool so the thread shows that
it is waiting (see `jstack` for the tool in your harness). Put all the context in the question:
the PR link, what blocks you, and the options with your recommendation first.

Ask only when you cannot continue alone:

- You cannot prove the change.
- The merge gate cannot pass, and you cannot fix that yourself.
- The next step is outside the grant above: deleting data, touching production,
  changing things outside the repo, closing a PR, or force-pushing any other
  branch.
- The goal is ambiguous in a way that changes the result.
- Another PR makes this one obsolete.

Decide everything else yourself with sensible defaults, and list those decisions
in the report.

If no question tool is available, or the tool returns no answer, take the safe
path: leave the PR open and unmerged, and start your final message with the
question.
