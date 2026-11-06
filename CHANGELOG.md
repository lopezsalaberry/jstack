# Changelog

Format follows Keep a Changelog. Versions are tagged `vX.Y.Z`; install a tag, not `main`.

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
