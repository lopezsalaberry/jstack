---
name: cross-review
description: "One-round review by a model from a different family, for high-risk changes only. The reviewer tries to break the change with a run; findings it cannot prove are dropped. Use when a change touches a high-risk area (listed below), or the operator asks for a cross-review."
---

# cross-review

A single review by a model from a different family than the author, for
high-risk changes:

- production data or schema migrations
- payments or billing
- auth, permissions, credentials
- concurrency or security
- production deploys of critical services

Everything else uses self-validation (`prove-it`, `verify-<app>`, tests, lint, build).

Reading a diff in the abstract mostly yields nitpicks and hypothetical risks. The
reviewer's job is to break the change by running it.

## Budget

- 1 round. One reviewer. The reviewer never starts subagents.
- Nits never trigger a new round. Budget end is not approval.

## 1. Scope

`git status --short`. After `git fetch origin`, find the base with
`git merge-base HEAD origin/<integration branch>`. The change is base to working
tree, with untracked files. Run the per-ticket gate first. Do not send code that
fails its own checks.

## 2. Pick the reviewer

Settings (see `jstack`): `reviewer_models`, `quota_probe`.

1. Walk `reviewer_models` in order and take the first entry whose provider is not
   the author's provider and that `quota-gate` reports as available (exit 0 or 2).
2. None available, or `reviewer_models` empty: do not block and do not wait. Start an
   independent review in a **fresh session of any model that is not the author's
   session**, preferably a different family. It sees only `git diff <base>` and the
   ticket's acceptance criteria, nothing of the author's reasoning. Start it with the
   harness's way to delegate a task (see `jstack`).
3. Whichever reviewer ran is held to the brief below exactly. Deterministic gates
   (tests, lint, build, `verify-<app>`) must be green before and after. Red gate, no merge.
4. After a merge reviewed by the fallback, run the repo gate on the merged head and keep
   that output in the evidence. Do not queue a second read-review. One exception: the
   change is high-risk and the reviewer left UNPROVEN findings. Then append one line
   to the file in the `posthoc_queue` setting
   (`<ISO date> <repo> <PR or sha> <base sha> <ticket> pending`, one per ticket), or,
   if the setting is empty, list the UNPROVEN items in the PR description.

If no reviewer can run at all, pause per `quota-gate`.

## 3. Brief

```
Break this change. Do not edit the repo, commit, push, comment, or start subagents.
Repo: <path> Base: <sha> Intent: <intent> Out of scope: <scope> Checks: <results>
See: git diff <base>.
Prove each finding with a run against the real code: a failing test, a repro
script, or command output that shows the wrong behavior. Put repros in a scratch
directory outside the repo (for example a temp worktree), never in the repo.
Report only what you ran. No style, no nits, no YAGNI, no hypothetical edge cases.
Reply: VERDICT: APPROVE or CHANGES, then for each finding:
S1 <file>:<line> <title> | cmd: <exact command> | got: <output> | want: <what the intent requires>
Findings you could not run (auth, permissions, credentials, or concurrency you
cannot reproduce here): list under UNPROVEN with the exact code path, one line each.
```

## 4. Answer

Rerun each finding's command yourself. It reproduces and breaks the intent: smallest
fix, and keep the repro as the regression test. It does not reproduce: drop it, with
one line saying what you ran. UNPROVEN items: read the code path; fix it only if you can
see the failure, and it never blocks on its own. Do not agree just to end the review.

## 5. Ledger and stop

Ship when no verified finding is open. If one stays disputed, show both sides in 2-3
lines and escalate. Put this block in the PR description so the review is auditable:

```
Cross-review: reviewer <model> (author <model>) | verdict <APPROVE|CHANGES>
Verified and fixed: <n> | Dropped (did not reproduce): <n> | UNPROVEN: <n> | Diff before/after: <lines>
```
