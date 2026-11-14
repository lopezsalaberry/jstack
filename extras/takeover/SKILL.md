---
name: takeover
description: "Finish a pull request, branch or agent thread that someone else started, or revive an old PR, and keep the original author's credit. Use when asked to take over, rescue, finish, or modernize a PR you did not start."
---

# Takeover

Someone else's work is evidence of intent, not proof of correctness. Decide whether it
should still exist, bring it up to date, prove it yourself, and finish it.

## 1. Read the state

PR description and review threads, checks, the branch's commits, and a `RUNSTATE.md` if an
agent left one (its `Next step` is the best lead). Note who the author is and what the PR
set out to do in one sentence.

## 2. Should it still exist?

- Fetch the integration branch. Is the goal already there? Search merged PRs and
  `git log origin/<integration branch> -S '<symbol>'`.
- Does an open PR overlap it? Run the overlap check from step 1 of `ticket`.
- Is its premise still true? A deleted module, a renamed API or a changed requirement
  can make the whole PR obsolete.

If it is obsolete or duplicated, stop. Closing it is outside your grant: report
`BLOCKED(decision)` with the evidence and your recommendation first. A worker started by `wave` never asks.

## 3. Bring it up to date, keeping their commits

- Work in a worktree as in step 1 of `ticket`, starting from their branch.
- Rebase onto the latest integration branch. Keep their commits and authorship; add your
  own commits on top rather than squashing theirs away. Resolve lockfiles by regenerating.
- Push to their branch only when you may (`--force-with-lease`, never a bare force). If the
  branch is on a fork you cannot push to, open a new PR from your branch and link theirs.

## 4. Re-prove everything

Their evidence is not yours. Reproduce the original failure or the missing behavior,
run the ticket's checks, and prove it as step 3 of `ticket` says. Fix what fails as its
step 5 says. Cut anything the goal does not need.

## 5. Finish

Continue `ticket` from its step 4 (or stop before merge when the repo
has a single integrator). In the PR description name the original author and PR, say what
you changed and why, and use the comment format from `leaving-pr-comments` for anything you
post on their thread.
