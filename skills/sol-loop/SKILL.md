---
name: sol-loop
description: "One-round cross-model review for high-risk changes only. The reviewer tries to break the change with a run; findings it cannot prove are dropped. Use when a change touches a high-risk area (listed below), or the operator says 'sol loop'."
---

> Adapted from [t3dotgg/tstack](https://github.com/t3dotgg/tstack) `sol-loop` @ `1085050f3baed1ac724caa4a8166145fb2ac88af`. Budget cut to 1 round, high-risk only, reviewer model not hardcoded. Prove-or-drop brief (2026-11-03) follows pstack `interrogate`: a finding survives only when a run proves it.

# sol-loop

A single review by a model from a different family than the author, for
high-risk changes:

- production data or schema migrations
- payments or billing
- auth, permissions, credentials
- concurrency or security
- production deploys of critical services

Everything else uses
self-validation (`prove-it`, `verify-<app>`, tests, lint, build).

Reading a diff in the abstract mostly yields nitpicks and hypothetical
risks. The reviewer's job is to break the change by running it.

## Budget

- 1 round.
- One reviewer. The reviewer never starts subagents.
- Nits never trigger a new round. Budget end is not approval.

## 1. Scope

`git status --short`. After `git fetch origin`, find the base with
`git merge-base HEAD origin/<integration branch>`. The change is base to working
tree, with untracked files.
Run the per-ticket gate first. Do not send code that fails its own checks.

## 2. Review

Pick a reviewer from a different model family than the author. Start it with
the harness's delegation tool (T3 `delegate_task`, Claude Code subagent, Codex
subagent). Check `$JSTACK_QUOTA_PROBE --model <reviewer model>` first.

If the other family has no quota (probe at 0%), do not block and do not wait:

- Run an independent Codex (`gpt-6.1-sol`) review in a fresh session, never
  the author's session or thread. It sees only `git diff <base>` and the
  ticket acceptance criteria, nothing from the author's reasoning.
- Use the brief below. The fallback reviewer is held to it exactly.
- Deterministic gates must be green before and after (tests, lint, build,
  `verify-<app>`). Red gate = no merge.
- Do not queue a Claude read-review of what you merged. After the merge, run
  the repo gate (`verify-<app>`, or its tests/build) on the merged head and keep
  that output in the evidence. The one exception: the change touches a high-risk
  area above and the fallback reviewer reported UNPROVEN findings. Then append one
  line to `~/base/state/posthoc-review.queue`:
  `<ISO date> <repo> <PR or sha> <base sha> <ticket> pending`, one line per
  ticket (not per commit). When Claude quota returns, rerun that reviewer's
  UNPROVEN items with the same brief.

If neither family has quota, pause per `quota-gate`.

Brief:

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

## 3. Answer

Rerun each finding's command yourself. It reproduces and breaks the intent:
smallest fix, and keep the repro as the regression test. It does not reproduce:
drop it, with one line saying what you ran. UNPROVEN items: read the code path;
fix it only if you can see the failure, and it never blocks on its own. Do not
agree just to end the review.

## 4. Stop

Ship when no verified finding is open. If one stays disputed, show both
sides in 2-3 lines and escalate. Report: model, verified findings fixed,
findings dropped (and why), UNPROVEN count, diff size before and after.
