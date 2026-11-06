## End-to-end flow (jstack)

1. Code changes for tickets: use `fanout`, also for a single ticket (a queue of one). Skip this flow for read-only tasks, questions, and docs-only edits.
2. Queue = ready tickets from this project's tracker, each with the files it expects to touch.
3. Each green ticket merges into the integration branch named in the settings below.
4. Prove every change on the real artifact (`prove-it`, this repo's `verify-<app>`, `evidence` in `.artifacts/`, tests, lint, build). Cross-model review only for `cross-review`'s high-risk list, 1 round.
5. On repeated failure follow `iterate` (no attempt cap: keep going while the checks move, stop by its rules). On quota follow `quota-gate`.

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
