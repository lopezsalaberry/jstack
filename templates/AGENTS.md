<!-- jstack-template: 0.10.1 -->

## End-to-end flow (jstack)

1. Code changes for tickets: use `fanout`, also for a single ticket (a queue of one). Skip this flow for read-only tasks, questions, and docs-only edits.
2. Queue = ready tickets from this project's tracker, each with `Touches:` (the files it expects to touch) and an observable `Done when:`. Write a missing one from the code before launch. To choose what to work on, use `groom`.
3. Each green ticket merges into the integration branch named in the settings below.
4. Prove every change on the real artifact (`prove-it`, this repo's `verify-<app>`, tests, lint, build). Start the evidence with the `evidence` skill's `checklist-init <ticket>` (it fills in the revision; once the proof is final, `proof-valid --stamp` fills in the patch id) and give every PASS its proof level, 1 to 5 (`prove-it`). A bug fix keeps `before.txt` and `after.txt` in `.artifacts/<ticket>/`. Cross-model review only for `cross-review`'s high-risk list, 1 round.
5. On repeated failure follow `iterate` (no attempt cap: keep going while the checks move, stop by its rules). On quota follow `quota-gate`.
6. UI changes (files matching `ui_paths` in the settings below): use only the tokens and components of the design system (`design_tokens`). If a ticket asks for a value they do not have (a size, a color, a font), do not hard-code it, even when the ticket gives the exact value: stop with `BLOCKED(decision)` naming the missing piece, so the design system is extended first (`ticket-start`, `full-send`). Every UI change shows a screenshot in its PR: run `evidence/scripts/publish <ticket> --pr <number>` (a path under `.artifacts/` shows the reader nothing), and put the before and after in your own messages.
7. A user-visible ticket that reports `INTEGRATED` moves to review in the tracker, not to done, with the PR and the proof, until the operator accepts.

## Session rules (any task)

- A decision the operator gives in the thread is recorded in the project's product doc, if it has one: the one place decisions live. Otherwise it is asked again next session.
- At the start of a session, run `wave-status` (see `fanout`), list the open PRs and relaunch what is `WAITING` before picking new work.
- When a wave drains, or the operator asks what is next, run `wrap-up`.

## jstack settings

Remove the lines you do not need. Every key and its default is in the `jstack` skill.

```
integration_branch: main
models:
reviewer_models:
review_bots:
ui_paths:
design_tokens: design/tokens.json
```

## Principles

1. Smallest change that fixes the case that happened (`full-send`).
2. Subtract before you add: dead code, single-use layers, repeated rules.
3. No speculative abstractions; extract only on real repetition.
4. Fix the root cause, not the symptom; reproduce the failure first.
5. Prove it on the real artifact (`prove-it`).
6. Every decision lives in exactly one place.
7. Fixed the same thing twice? Encode it as a script, test or lint, not more prose.
8. One ticket, one isolated branch, small steps each ending in a check; never work directly on the integration branch.
