---
name: evidence
description: "Record local proof that a ticket's behavior works: a checklist of test targets with pass/fail, numbered screenshots, and an optional screen recording, saved under .artifacts/ and summarized in the PR. Use while proving any change with observable behavior."
---

# Evidence

Test the change the way a user would and keep what you saw. How to launch and
drive the app (machine, device, browser, simulator) comes from the repo's
`verify-<app>` skill, not from here.

## 1. Targets

Write each thing the ticket asks for as a testable statement, for example
"It should save the note and show it in the list". Size the evidence to the
change: interactive flows get screenshots or a recording, CLI and API changes
get command and output pairs, docs-only edits get none.

## 2. Capture

Save everything to `.artifacts/<ticket>/` (keep `.artifacts/` out of commits).

- **Headless UI:** drive it with Playwright locally and save numbered
  screenshots: `01-start.png`, `02-<step>.png`, ...
- **GUI:** drive it live and, when the platform allows, record the screen with
  the OS or harness recorder. Recording is optional.
- **CLI or API:** save each command with its real output.

Note the revision under test: `git rev-parse HEAD` and the branch.

## 3. Checklist

Run `scripts/checklist-init <ticket>` first, even for a one-line fix. It creates
`.artifacts/<ticket>/checklist.md` with the revision, the patch id and the table already laid out
(and keeps `.artifacts/` out of commits). Then fill one row per target: `PASS` or `FAIL`, the proof
level from `prove-it`, what you saw, and the screenshot or output file. For a bug fix also keep
`before.txt` (the failing output before the fix) and `after.txt` (the passing output after it).
A small change gets a short checklist, never no checklist: it is what lets `proof-valid` tell a
later reader whether the proof still describes the patch.
A target you could not exercise is `FAIL`, not skipped. Never weaken a target
to make it pass.

## 4. Report

Paste the checklist summary into the PR description and attach the
screenshots or video when the harness can attach files. Do not publish
evidence anywhere else.
