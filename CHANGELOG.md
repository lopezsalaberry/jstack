# Changelog

Format follows Keep a Changelog. Versions are tagged `vX.Y.Z`; install a tag, not `main`.

## 0.9.4

### Fixed
- `token-lint` no longer checks test files (`__tests__/`, `*.test.*`, `*.spec.*`). Run over the last 40 commits of two real
  repos with the UI paths set for the first time, it reported 10 violations and every one was inside a test (a color a test
  asserts on, `rgb(colors.x)` in a helper). A test is not a UI change, and with the gate on those would have blocked merges.

## 0.9.3

### Added
- `doctor` says when the UI design gate is off. A repo with `design/tokens.json` and no `ui_paths` has no file that counts as
  UI, so the design check never ran and nothing said so. Found by reading 24 hours of runs: 27 sessions edited UI files in
  five repos that all had a design system, and none ran `token-lint`; none of the five set `ui_paths`.
- `scripts/template-drift`: says which repos carry an older copy of `templates/AGENTS.md`. The template now starts with a
  version marker, `<!-- jstack-template: X.Y.Z -->`, which a test ties to this changelog, so it moves when the template does.
  `doctor` repeats the check for its repo. Found in the same 24 hours: three of five repos still had the 0.5.4 flow, none had
  the `wrap-up` line, and no session had loaded `wrap-up` or `groom`.
- `doctor --check-updates` compares the checkout with the newest `vX.Y.Z` tag on its `origin`. It needs the network, so it is
  off by default, and a failed lookup is a warning.

### Changed
- `templates/AGENTS.md` starts with the version marker (the rules themselves are unchanged).

## 0.9.2

### Fixed
- `quota-gate`: the shipped `quota-probe` now hands any call without `--source` to the command the `quota_probe` setting
  names when that is a different one. A session that ran the shipped file directly read "unknown (no quota source
  configured)" for a provider the configured probe knew to be at 0%, wrote it down as fact, and two days later started a
  review on that provider, which never answered. Whichever probe a caller reaches now gives the same answer.
- `quota-gate`: a reading is for the launch that asked for it; "unknown" from earlier in a session, or from a probe that is
  not the configured one, is not data.
- `cross-review`: choosing a reviewer says to run `<quota_probe> --provider <provider>` for every candidate before starting
  any, not to guess from the model list, and the ledger carries a `Probed:` line with the exit codes. After starting a
  reviewer the parent does not end its turn: the new action "Check that a started agent answered" in `jstack` is the
  2-minute check that silence is a refusal.

## 0.9.1

### Fixed
- `evidence`: a checklist started with `checklist-init` before the change existed recorded an empty patch and the
  base's tip as its revision, so the first `proof-valid --checklist` after the change answered "landed" and exit 0 for
  any patch. Found by an independent review of `wrap-up`. `proof-valid --checklist` now refuses a checklist that
  records no patch (exit 2, naming the fix), `proof-valid --stamp FILE` writes the current revision and patch id once
  the proof is final, and `checklist-init` says so when the patch is still empty.

## 0.9.0

### Added
- `wrap-up`: the last phase of a wave, run by the parent. It validates what the workers reported (the real artifact
  and not the summary, scope against `Touches:`, the proof against the patch, the gate again, each acceptance
  criterion, and an independent review when a high-risk or user-visible change has no verdict for its patch),
  offers every merge to the operator in one question that also carries the recommended next step, acts on the answer
  and records it.
  Found by reading 12 hours of runs: 1 of 21 closing reports said what to do next, `cross-review` was loaded in none
  of the sessions, and four candidates the workers had reported ready were waiting for someone to validate and
  integrate them.

### Changed
- `fanout` ends with "run `wrap-up`", and the `templates/AGENTS.md` session rules carry the same line.

## 0.8.3

### Changed
- The wait for a started model's first output is 2 minutes, not 10. Measured on 643 healthy sessions: the first
  output arrives in 3 to 4 seconds at the median, 8 to 14 seconds at the 99th percentile, 20 seconds at worst, and none
  took a minute. Five sessions out of 170 never produced anything at all, so the silent start was not a one-off.

## 0.8.2

### Fixed
- A probe that does not understand the contract looked exactly like a probe with no data. `argparse` exits 2 on a
  bad argument and 2 means "unknown" in `quota-gate`, so a probe that only knew its own flags answered every
  `--provider` call with exit 2: every provider looked unknown, and `--mark-exhausted` never wrote the mark that stops
  other workers from retrying a provider that just refused. `doctor` saw exit 2 and said ok. Found when a review on an
  account in a quota cooldown sat silent for seven hours. The shipped `quota-probe` now exits 64 on a bad argument, and
  `doctor` walks the whole contract (`--provider`, `--mark-exhausted`, `--clear`) with a throwaway name and marks file,
  and fails on a usage error.
- A silent start is a refusal. An exhausted account can hold a turn open without any error, so "start it, and if it
  fails go to the next candidate" never moved on. `quota-gate` and `cross-review` now wait at most 10 minutes for the
  first output and treat silence like a refusal: stop it, mark the provider, take the next candidate.

## 0.8.1

### Fixed
- `groom` listed "already on the integration branch" as a reason to CANCEL. Work that is already merged is
  delivered, not canceled. It now has its own verdict, DELIVERED: move it to review with the commit and PR,
  never to canceled, and it is done only when the operator accepts. A commit that names the ticket is not
  proof that its acceptance criteria hold, so the skill says to name what was not checked. It also says to
  give no verdict on a ticket it could not verify. Found the first time it ran on a real backlog: 8 tickets
  still in Todo had been merged five days earlier.

## 0.8.0

### Added
- `groom`: a skill the operator runs by hand to clean and rank the backlog and choose what to work on.
  It proposes one verdict per ticket (a cancel needs named evidence), checks that what stays on top is
  ready (`Touches:` and an observable `Done when:`), and puts every decision the operator owes in one
  question. It changes the tracker only after a yes, and remembers parked tickets in the tracker itself,
  so it keeps no file of its own. Nothing about it is scheduled.

### Changed
- `templates/AGENTS.md` carries four more rules, for the reason 0.7.2 found (a rule that lives only in a
  skill is followed only when the agent loads the skill): a ticket enters the queue with `Touches:` and
  `Done when:`; a user-visible ticket that integrates stays in review until the operator accepts; a
  decision the operator gives goes into the product doc; a session starts with `wave-status` and the open PRs.

## 0.7.5

### Fixed
- `doctor` crashed on a Python new enough to have removed `load_module()` (a MacBook with a recent
  Homebrew Python). It now loads its sibling module the supported way. A test runs every shipped script
  with deprecation warnings as errors, so the next removal is caught here and not on a Mac.

## 0.7.4

### Fixed
- A checkout path with a space (an external disk called "Crucial X9") broke the default `quota_probe`
  command and made `doctor` crash. The default is now shell-quoted, `doctor` splits commands the way a
  shell does, and a probe that cannot run is reported as a failed check instead of a traceback. Found by
  running the doctor on the Mac mini.

### Changed
- `doctor` also checks `~/.codex/skills`. Found because that folder was still on the old install.

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
