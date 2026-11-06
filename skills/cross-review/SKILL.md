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

Settings (see `jstack`): `reviewer_models`, `quota_probe`. The reviewer must never be the
reason a change is stuck: there is always a next candidate, and a refusal sends you to it.

1. **Candidates, in order.** The entries of `reviewer_models`. An entry `auto` stands for every
   model the harness can start (list them with the "List the models" action in `jstack`), models
   from a family other than the author's first. Drop any candidate that is the author's own
   session.
2. **Skip what is known to be out.** Ask `quota-gate` about each candidate's provider. Exit 1 (at
   0% or marked exhausted): skip it. Exit 0 or 2: it is a candidate.
3. **Try it.** Start the reviewer with the harness's delegate action. If it fails for quota, rate
   limit, authentication or availability, mark the provider exhausted as `quota-gate` describes
   and go to the next candidate immediately. Do not retry the same provider and do not wait.
4. **Independence ladder.** Take the best level any candidate gives, and write it in the ledger:
   - **L1** a model from another family than the author's.
   - **L2** a different model from the same family.
   - **L3** a fresh session of any model that is not the author's session, seeing only
     `git diff <base>` and the acceptance criteria. This level is always available if any model
     can start at all.
   When the harness does not say which family a model belongs to (an automatic router, for
   example), record "family unknown" instead of claiming L1.
5. Whichever reviewer ran is held to the brief below exactly. Deterministic gates (tests, lint,
   build, `verify-<app>`) must be green before and after. Red gate, no merge.
6. After a merge reviewed at L2 or L3, run the repo gate on the merged head and keep that output
   in the evidence. Do not queue a second read-review. One exception: the change is high-risk
   and the reviewer left UNPROVEN findings. Then append one line to the file in the
   `posthoc_queue` setting (`<ISO date> <repo> <PR or sha> <base sha> <ticket> pending`, one per
   ticket), or, if the setting is empty, list the UNPROVEN items in the PR description.

If every candidate refuses, including L3, no model can start: pause per `quota-gate`.

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
Cross-review: reviewer <model> (author <model>) | independence <L1|L2|L3|family unknown> | verdict <APPROVE|CHANGES>
Skipped before this one: <provider: reason, or none>
Verified and fixed: <n> | Dropped (did not reproduce): <n> | UNPROVEN: <n> | Diff before/after: <lines>
```
