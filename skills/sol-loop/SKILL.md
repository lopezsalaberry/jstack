---
name: sol-loop
description: "One-round cross-model review for high-risk changes only. Use when a change touches a high-risk area (listed below), or the operator says 'sol loop'."
---

> Adapted from [t3dotgg/tstack](https://github.com/t3dotgg/tstack) `sol-loop` @ `1085050f3baed1ac724caa4a8166145fb2ac88af`. Budget cut to 1 round, high-risk only, reviewer model not hardcoded.

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
- Use the adversarial brief below plus: "Assume this diff is wrong. Your job is
  to find the case that breaks it."
- Deterministic gates must be green before and after (tests, lint, build,
  `verify-<app>`). Red gate = no merge.
- Queue a post-hoc Claude review: append one line to
  `~/base/state/posthoc-review.queue`:
  `<ISO date> <repo> <PR or sha> <base sha> <ticket> pending`. When Claude
  quota returns, review it with the same brief and open a follow-up ticket for
  any blocker or should.

If neither family has quota, pause per `quota-gate`.

Brief:

```
Review only. Do not edit, commit, push, comment, or start subagents.
Repo: <path> Base: <sha> Intent: <intent> Out of scope: <scope> Checks: <results>
See: git diff <base>. Find bugs, broken callers, mismatch with intent.
blocker = intended case wrong. should = real bug callers will hit. nit = rest.
Reply: VERDICT: APPROVE or CHANGES, then S1 [blocker|should|nit] <file>:<line> <claim>. Fix: <hint>
```

## 3. Answer

Check each finding yourself. Agree: smallest fix, one focused test if needed.
Disagree: say why with evidence. Nits and out-of-scope: decline in one line,
list as follow-up. Do not agree just to end the review.

## 4. Stop

Ship when no blocker or should is open. If one stays disputed, show both
sides in 2-3 lines and escalate. Report: model, findings fixed and declined,
diff size before and after.
