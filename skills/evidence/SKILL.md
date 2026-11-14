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
(and keeps `.artifacts/` out of commits). Started before the change exists, it records an empty patch:
when the proof is final, run `scripts/proof-valid --stamp .artifacts/<ticket>/checklist.md` so the checklist names
the patch it proves. Then fill one row per target: `PASS` or `FAIL`, the proof
level from `prove-it`, what you saw, and the screenshot or output file. For a bug fix also keep
`before.txt` (the failing output before the fix) and `after.txt` (the passing output after it).
A small change gets a short checklist, never no checklist: it is what lets `proof-valid` tell a
later reader whether the proof still describes the patch.
A target you could not exercise is `FAIL`, not skipped. Never weaken a target
to make it pass.

**Prove it where it has to work.** When the ticket names a device, a browser or the packaged app,
that is the surface: start with `scripts/checklist-init <ticket> --surface <name>`, reach it as the
repo's `verify-<app>` skill says, and give it a row at level 5 with that name in the Surface
column. Proof elsewhere is a stand-in: it does not pass, and `proof-valid --checklist` says so. A
desktop browser at a phone's width is not the phone. If you cannot reach the surface, report
`BLOCKED(env)` with what you tried, never a quiet switch to another surface, and never a note that
leaves the check to the operator.

## 4. Report

Paste the checklist summary into the PR description. A path under
`.artifacts/` is not evidence for the person reading the PR: that folder is not
in git, and a PR that says "screenshots are under .artifacts/" shows nothing.

When anything on a screen changed, run `scripts/publish <ticket> --pr <number>`.
It copies the images and videos to `refs/jstack-evidence/<ticket>` on `origin` (a ref
of its own, which a normal clone or fetch does not download) and puts them in the
PR description as pictures, replacing the block of an earlier run. Name the few files
that carry the proof (`publish <ticket> <file> ...`); it refuses a whole folder. Run it again
after the proof changes. It works only for a GitHub origin; for any other, it
says so and lists the files: show them in your message instead. Do not publish
evidence anywhere else.

Show the screenshots that matter while you work, not only at the end: the
before and the after of a visible change belong in your own message, as images
when the harness renders them. `scripts/pr-evidence-check --pr <number>`
exits 1 when a change to `ui_paths` files has no picture a reviewer can open in
its PR.
