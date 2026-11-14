---
name: review
description: "One round by an agent that did not write the change. Break mode, for high-risk changes: the reviewer tries to break it by running it. Verify mode, for user-visible changes: the reviewer uses it as a user would. Use for a high-risk or user-visible change, or when the operator asks."
---

# Review

An author checks what it meant to build. One round by someone else catches the rest. Green CI and a bot's approval
are not this review: neither runs the change.

| Mode | When | The reviewer |
|---|---|---|
| **Break** | The change touches production data or migrations, payments, auth or credentials, concurrency, security, a production deploy, or a shared component or module that many screens or callers go through | tries to break it with a run; what it cannot prove is dropped |
| **Verify** | The change is user-visible (screens, command output, API responses) and `verify_mode` is not `off` (`always` means every code change) | uses the delivered artifact as a user would, criterion by criterion |

Everything else relies on the author's own proof (`ticket`). One round, one reviewer, and the reviewer starts no
other agents. Nits never start a second round.

## 1. Before you ask

`git fetch origin`; the change is everything from `git merge-base HEAD origin/<integration branch>` to the working
tree. Run the ticket's own checks first: do not send code that fails them.

## 2. Pick the reviewer

The reviewer must never be why a change is stuck. Walk `reviewer_models` (see `jstack`) in order. An entry is
`provider:model`, a bare `provider` (a model of another family than the author's) or `auto` (anything the harness
can start, other families first). Never the author's own session. When only the author's provider answers, take
another model of it before the author's own model, and the cheaper of two that are equally independent: a review
needs a different pair of eyes, not the strongest model.

1. **Probe, then start.** For each candidate run the `wave` skill's `scripts/quota-probe --provider <provider>`.
   Exit 1: skip it. Exit 0 or 2: start it, naming its model and effort. A list of models says what can start, not
   what has quota.
2. **Two minutes.** Do not end your turn. If it refuses (quota, rate limit, authentication, unavailable) or shows
   nothing in 2 minutes, stop it, run `scripts/quota-probe --mark-exhausted <provider>` (add `--until <date>` when
   the refusal names when it comes back) and take the next candidate at once.
3. **Never stop to ask which provider to use** while a candidate is left. The list is the operator's permission
   to fall through it, and no remembered preference overrides it.
4. **Say how independent it was**, the best level any candidate gave: **L1** another model family; **L2** another
   model of the author's family; **L3** a fresh session of any model that sees only the diff and the criteria. L3
   is there whenever any model can start. If the harness does not say the family, write "family unknown".

If nothing can start at all, report `WAITING` until a probe passes. That is the only wait.

## 3. The brief

Break:

```
Break this change. Do not edit the repo, commit, push, comment or start other agents.
Repo: <path> Base: <sha> Intent: <intent> Out of scope: <scope> Checks: <results>   See: git diff <base>
Prove each finding by running the real code: a failing test, a script, or command output that shows the wrong
behavior. Keep scratch files outside the repo. Report only what you ran. No style, no nits, no hypotheticals.
Reply: VERDICT: APPROVE or CHANGES, then per finding:
<file>:<line> <title> | cmd: <exact command> | got: <output> | want: <what the intent requires>
What you could not run (auth, credentials, concurrency you cannot reproduce): list under UNPROVEN with the code path.
```

Verify:

```
Do not edit the repo, commit, push, comment or start other agents.
Repo: <path> Base: <sha> Head: <sha> Intent: <intent> Acceptance criteria: <list>
Use this change the way a user would, on the delivered artifact (the project's verify-<app> skill if it has one),
base against head, on this surface: <the one the ticket names, or the repo's main one>. For each criterion give the steps and what you saw. If it touches the UI, compare the screens
with the design source and list every mismatch.
Reply: VERDICT: PASS, PASS+NOTES or FAIL, then one line per criterion. What you could not run is UNPROVEN, never PASS.
```

## 4. The answer

Act on each finding as it arrives; do not edit the checkout while the reviewer is still reading it. Run the
finding's command yourself. It reproduces and breaks the intent: smallest fix, and the reproduction stays as a
test. It does not reproduce: drop it and say what you ran. `UNPROVEN`: read the code path, fix only what you can
see fail, and list the rest in the PR under "Not in this change"; it never blocks by itself. `FAIL` blocks; notes
under `PASS+NOTES` are follow-ups. When the ticket names a surface, the verifier's run there is the level 5 row of
the checklist. Do not agree in order to finish. If a finding stays disputed, show both sides in
three lines and report `BLOCKED(decision)`.

Checks must be green before and after. Then write the verdict in the PR, under "Who did the work":

```
Review: <break|verify> by <model> | independence <L1|L2|L3|family unknown> | verdict <APPROVE|CHANGES|PASS|PASS+NOTES|FAIL> | patch <id>
```

`<id>` is the `Patch-id:` that `ticket`'s `scripts/proof-valid --print` gives. The verdict covers that patch: a
rebase keeps it, a new edit needs a fresh verdict, and `check` reads this line.
