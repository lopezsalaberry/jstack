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

Pick a reviewer from a different model family than the author. Start it with the harness's delegation tool (T3 `delegate_task`,
Claude Code subagent, Codex subagent). If no other model family is
reachable, report BLOCKED instead of substituting the same model.

Temporary (until 2026-11-04, while Sol/Codex has no credits): the reviewer may
be a fresh-context Claude Sonnet session that sees only the diff and the ticket
acceptance criteria. Same brief, same 1 round.

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
