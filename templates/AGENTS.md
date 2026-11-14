<!-- jstack-card -->
## How work is done here (jstack)

1. **A code change is a ticket.** Use the `ticket` skill: its own worktree and branch, never the integration branch. Reading, answering and docs-only edits skip this.
2. **Prove it before you say it.** Run the `ticket` skill's `scripts/checklist-init <ticket>` before the change. A target is PASS only if you ran it. A bug fix keeps the failing output from before the fix.
3. **UI changes use the design system.** In files matching `ui_paths`, use only the tokens and components of `design_tokens`. A value they do not have is `BLOCKED(decision)`, even when the ticket gives the exact value. Show the before and the after in your message and in the PR (`scripts/publish`).
4. **One gate.** Before you merge or hand over, `scripts/check <ticket> --pr <number>` prints no FAIL. Paste what it prints in the PR.
5. **Someone else looks.** A high-risk or user-visible change gets the `review` skill. Take the first reviewer in `reviewer_models` that answers, and never stop to ask which one while a candidate is left.
6. **Delegating is a brief.** Write each worker's brief with the `wave` skill's `scripts/brief`, which makes you name its model and effort. Several tickets: the `wave` skill.
7. **Out of budget is not failure.** When quota, a rate limit, time or context runs out: push a WIP commit, write `RUNSTATE.md`, report `WAITING <condition>`.
8. **End with the state and the next step.** `INTEGRATED <sha>`, `READY_FOR_INTEGRATOR`, `WAITING <condition>` or `BLOCKED(env|task|decision) <reason>`. Then what changed, what you did not verify, and one recommendation.

Smallest change that fixes the case that happened. Fix the cause, not the symptom. Fixed the same thing twice: make it a script or a test, not more prose.
<!-- /jstack-card -->

## jstack settings

Remove the lines you do not need. Every key and its default is in the `jstack` skill.

```
integration_branch: main
ui_paths:
design_tokens: design/tokens.json
```
