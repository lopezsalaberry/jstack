# Changelog

Format follows Keep a Changelog. Versions are tagged `vX.Y.Z`; install a tag, not `main`.

## 1.0.0

The same premises with a third of the text. Measured before this: in 143 sessions, the tools that are one command were
used (`checklist-init` in 74, `proof-valid` in 64) and the rules that were only prose mostly were not (`RUNSTATE.md` in
34%, `wrap-up` in 4 sessions, `iterate` in 2, the trail in 1); four skills were never loaded; the skills had grown from
8,600 to 13,200 words in eight days. So each rule moved to where it is followed: a script when a command can check it, a
short card when every session must know it, a skill for the rest.

### Added
- `ticket/scripts/check`: the merge gate as one command (branch, clean tree, up to date, proof, design, and with `--pr` the
  PR's head, screenshot, review verdict, CI and mergeability). The worker pastes its output; the orchestrator reruns it.
- `wave/scripts/brief`: writes a worker's brief from the ticket and the repo's settings, adds the design block for a UI
  ticket, and does not run without `--model` and `--effort`.
- The rules card: eight rules at the top of `templates/AGENTS.md`. `install.sh --card FILE` writes or replaces it in a
  repo's `AGENTS.md` or in the file a harness loads for every repo, so one copy can serve a machine. `doctor` checks it.
- `install.sh --extras` links the skills in `extras/`.
- `tests/test_budget.py`: the skills and the card have a word budget.

### Changed
- Seventeen skills became five. `ticket` holds what `ticket-start`, `full-send`, `file-pr`, `prove-it`, `evidence` and
  `iterate` held; `review` is `cross-review`; `wave` holds `fanout`, `quota-gate` and `wrap-up`. `babysit-pr`, `takeover`,
  `leaving-pr-comments`, `create-verify` and `correct-mistakes` moved to `extras/` and are not installed by default.
- `publish` builds a Before / After table (the base commit beside the head, one row per state, from files named
  `before-<state>` and `after-<state>`), with a "Not shown" line. It publishes the few named files, not the folder: real
  evidence folders averaged 10 MB per ticket. The files go to `refs/jstack-evidence/<ticket>`, which a normal fetch or
  clone does not download, instead of a branch every worker would fetch. One ref per ticket also ends the race between
  two workers pushing to one branch.
- A pull request ends with "Who did the work", and the review verdict is one `Review:` line that `check` reads.
- `quota-probe` always handles the refusal marks itself and hands only the reading to a configured `quota_probe`, which
  now has to answer one question (`--provider NAME`).
- `RUNSTATE.md` is written when a worker stops before the end, not at every step.
- The repo's `AGENTS.md` copy is the card plus the settings block; `templates/AGENTS.md` no longer carries a version
  marker and the long flow.

### Fixed, from an independent review before release
A reviewer of another model family ran both versions blind and proved these with commands; each is now a test.
- `check` passed a row marked "unproven", a level cell that still held the hint "1 to 5", a branch with no change, a
  detached HEAD, a link that is not a picture file, a `Review:` line with no patch id, and a PR GitHub had not yet
  called mergeable. All fail now. With no UI file changed it says it cannot tell whether the change needs a review.
- `proof-valid` called a checklist that records no patch valid when HEAD had no change, and called a proof "landed"
  when HEAD had moved on to a later, unproven patch.
- `quota-probe` exited 2 ("unknown, go ahead") on a source line it could not read; it exits 64. `--until` has a 92-day
  bound again, so a mistyped year cannot hide a provider for good and a reset on the 1st is still accepted.
- `token-lint` did not look at arbitrary utility sizes such as `p-[13px]`.
- `brief` added the design block for any folder when a `ui_paths` glob started with `**`; it now reads the repo's files.
- `wave-status` printed `?: ? -> ?` for a `RUNSTATE.md` without a metric. `publish --dry-run` needed an `origin`.
- `pr-wait` ships with `ticket`, so a harness with no PR watcher has one in a default install.

### Removed
- Settings `models` (say it in `routing`), `review_bots` and `advisory_bots` (options of `pr-wait`), `quota_source`,
  `quota_max_age_minutes`, `iteration_minutes`, `posthoc_queue` and `paid_fallback`. `doctor` names any that a repo still
  sets.
- `trail`, `template-drift` (the card check in `doctor` replaces it), `pr-evidence-check` (now a line of `check`) and
  `docs/OPERATING-MODEL.md`.

## 0.10.1

The reader of a pull request can see the screenshots. Measured over two weeks of four real repos: of 214 pull requests that
touched UI files, 3 showed an image, 103 said the screenshots were "under `.artifacts/`" (a folder that is not in git, so the
reader sees nothing), 50 only named the word and 58 said nothing. `evidence` told agents to attach screenshots "when the harness
can attach files", and `gh` cannot.

### Added
- `evidence/scripts/publish TICKET [--pr N]`: copies the images and videos of `.artifacts/<ticket>/` to a `jstack-evidence`
  branch of `origin` (git plumbing: the working tree, the index and the repo's branches are not touched; one commit per run; the
  same files twice make no second commit) and prints markdown that shows them. With `--pr` it puts the block in the PR
  description, replacing an earlier run's. A non-GitHub origin gets the list of files and exit 2 instead of a broken link.
- `evidence/scripts/pr-evidence-check --pr N`: exits 1 when a change to `ui_paths` files has no picture or video a reviewer can
  open in its PR or comments. A path under `.artifacts/`, a status badge and an avatar do not count.

### Changed
- `templates/AGENTS.md` (marker 0.10.1): rule 6 asks every UI change to show a screenshot in its PR and the before and after in
  the agent's own messages. Repos with an older copy show up as `stale` in `template-drift` and `doctor`.
- `full-send`'s merge gate asks for `pr-evidence-check` instead of "screenshots attached", and `wrap-up` runs it for UI changes.
- `evidence` step 4 says what `.artifacts/` is not.

## 0.10.0

The orchestrator chooses the model for each task, and a review always has somewhere to go. Found by reading the last
week of runs: two independent reviews stopped on 11 and 13 November because their provider had reached a monthly cap and a
remembered note said "ask before using another one"; the deploy behind the first waited for hours.

### Added
- `routing` setting: free text the orchestrator reads when it picks a model ("UI and UX work: the strongest model; native
  builds: provider-b"). A suggestion that the orchestrator may depart from, saying why in the trail. `models` is now a pin:
  set, it is walked in order as before (with `inherit-parent` as an entry); empty, the orchestrator picks per task from what
  the harness can start.
- The operator's own settings file, `~/.config/jstack/settings` (or `$JSTACK_USER_SETTINGS`): plain `key: value` lines that
  apply to every repo on the machine. Precedence is environment, then the repo's `AGENTS.md`, then this file, then the default.
- `quota-probe --mark-exhausted NAME --until WHEN` (and the same in the base probe): the mark lasts until the moment the refusal
  names, an ISO date or date-time or epoch seconds. A past time, one more than 45 days away, or both `--minutes` and `--until`
  exit 64. The default hour made a monthly cap look available again every hour.
- `reviewer_models` accepts a bare provider (its strongest model of another family than the author).

### Changed
- Every delegate names its model and effort (`quota-gate`, "Pick the model"). A child that is not told inherits its parent's, so
  an orchestrator on the strongest model would run every worker on it. Unwatched work records the choice as a `delegate` row in
  the trail. Effort starts from the session's level: one step up for the hardest work, one or two down for routine work, and
  never changed on a verifier or reviewer.
- `cross-review`: the list is the operator's permission to fall through it, so no remembered preference turns a refusal into a
  question. The author acts on each finding as it arrives, does not edit the checkout under review, and does not wait for a
  reviewer the operator called non-blocking.
- `fanout`: a worker that stopped because its provider refused is relaunched at once on the next candidate; it is parked only
  when no candidate can start.
- `wrap-up`: starts from what the wave launched, not from what reported, and sends work back to a fresh worker with the whole
  brief instead of messaging the old one.

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
