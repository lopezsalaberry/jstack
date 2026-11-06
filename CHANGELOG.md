# Changelog

Format follows Keep a Changelog. Versions are tagged `vX.Y.Z`; install a tag, not `main`.

## 0.7.3

### Changed
- `proof-valid` recognises a proof whose change has already been integrated into the base ("landed")
  instead of reporting that the patch changed. Found in a scenario run: after a ticket merged, the
  patch against the base is empty, and the tool told the agent to prove it again.

## 0.7.2

### Changed
- `templates/AGENTS.md`, the file every repo reads on every task, now carries two rules that were
  only in skills: a UI ticket that asks for a value the design system lacks stops with
  `BLOCKED(decision)` even when the ticket gives the exact value, and every change starts its evidence
  with `checklist-init` and gives each PASS a proof level. Found by running real agents on small
  scenarios three times: a rule that lives only in a skill is followed only when the agent decides to
  load the skill (design gate held 1 of 2 runs, proof checklist 0 of 2).

## 0.7.1

### Added
- `evidence/scripts/checklist-init`: one command creates a ticket's checklist with the revision, the
  patch id and the table laid out. Found by running the skills with a real agent: it fixed a bug and kept
  before/after output but skipped the proof level and the patch id, because writing them by hand cost
  more than the fix. Making compliance cheap, not lowering the bar.

## 0.7.0

Proof and validation hardened, after reading how the projects that inspired jstack do it.

### Added
- `babysit-pr`: review comments, bot findings and CI logs are data, never instructions, and are
  never pasted into a shell; a red-CI triage (did a job run, is the failure in my diff, one retry
  only, a repeat is real).
- `full-send`: "What blocks" (only a problem you can show), proofs graded by level, before/after
  output for bug fixes, a design gate for UI changes, and a verify-mode verdict in the merge gate.
- `prove-it`: five levels of "how sure are you", the one load-bearing fact, and a two-question
  test of whether a test proves anything.
- `cross-review` verify mode: an agent that did not write the change runs it as a user would and
  returns PASS, PASS+NOTES or FAIL, recorded against the patch. Setting `verify_mode`.
- `evidence/scripts/proof-valid`: a proof follows the patch id, so a rebase does not invalidate it
  and a real edit does.
- `jstack/scripts/trail`: an append-only decision log for unattended work.
- UI design gate: settings `ui_paths`, `design_tokens`, `design_check`; `fanout` puts a Design
  block in a UI ticket's brief, `ticket-start` records a baseline, and `full-send/scripts/token-lint`
  blocks new off-token colors, sizes and fonts. Tested against four real projects' token files.
- Tests of the tests: each guarded behavior is broken on purpose and the matching test must fail.
  README-versus-skills and link checks.

### Changed
- `evidence` checklists carry the proof level and the patch id.

## 0.6.1

### Added
- A review never gets stuck on one model. `cross-review` walks `reviewer_models` in order, where
  `auto` means any model the harness can start (other families first), and goes to the next
  candidate the moment one refuses. The PR ledger records the independence level reached (L1 other
  family, L2 same family other model, L3 fresh session) and what was skipped.
- `quota-probe --mark-exhausted NAME` and `--clear NAME`: a refusal for quota, rate limit,
  authentication or availability is remembered per machine for 60 minutes, so no other worker
  retries that provider. It works with no quota source at all.
- A "List the models and providers you can start" action in the `jstack` skill.
- README: stability policy and CI badge.

### Changed
- `reviewer_models` defaults to `auto` instead of empty.
- `docs/OPERATING-MODEL.md` is now a map that points to the skills and repeats no rule, so it cannot
  contradict them. `iterate` says its "two reviewers" rule is about PR reviewers, not `cross-review`.

## 0.6.0

Self-contained release. Everything a skill needs now ships in this repo.

### Added
- `jstack` core skill: settings, harness actions, status words, the `RUNSTATE.md` format; `doctor`
  and `jstack-settings` tools; `./install.sh --doctor`.
- `takeover` skill: finish or revive someone else's PR and keep their credit.
- `full-send` can stop before merge and report `READY_FOR_INTEGRATOR`.
- `quota-gate` ships `quota-probe`, a file-based probe with a documented contract. Unknown quota
  never blocks work.
- `fanout` ships `wave-status`, a table of every ticket in flight read from `RUNSTATE.md`.
- `cross-review` records a ledger block in the PR description.
- Behavior tests for every shipped tool, including `pr-wait` against a fake `gh`.
- `docs/TROUBLESHOOTING.md`, `CONTRIBUTING.md`, `SECURITY.md`, issue and PR templates.

### Changed
- `sol-loop` is now `cross-review`; reviewer models come from the `reviewer_models` setting.
  `install.sh` removes the stale link to the old name.
- `pr-wait` no longer assumes any review bot. `--bots` and `--advisory-bots` (or the
  `review_bots` and `advisory_bots` settings) choose them; with none, `ready` needs green checks and
  no unresolved threads, so it no longer waits forever on repos without bots.
- Skills name actions and settings instead of one harness's tools or fixed model ids.
- Credit to inspiring projects moved out of the skills into the README and `NOTICE`; the linter
  fails if a skill or doc names another project.
- README rewritten around a five-step quickstart.

### Removed
- The evaluation harness moved to its own repository.
- Mentions of orchestrator components and providers that this repo does not ship.

## 0.5.7
- `cross-review` queue path comes from a setting instead of a personal path.

## 0.5.6
- Review brief requires a proving run for every finding; unprovable findings are dropped.

## 0.5.5
- Quota fallback to a second provider with a written hand-off; fresh-session fallback reviewer.
