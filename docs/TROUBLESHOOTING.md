# Troubleshooting

Start with `./install.sh --doctor`. It prints one line per check (`ok`, `warn`, `FAIL`) and
exits 1 on a `FAIL`.

| Symptom | Cause and fix |
|---|---|
| `FAIL gh` or `FAIL gh authenticated` | The GitHub CLI is missing or signed out. Install it from https://cli.github.com, then `gh auth login`. |
| `warn UI design gate: OFF` | The repo has design tokens but no `ui_paths`, so no change counts as a UI change and the design check never runs. Add `ui_paths: <globs of the UI files>` to the `## jstack settings` block. |
| `warn AGENTS.md matches the current template` | The repo's copy of the flow predates the current template, so its agents do not read the newer rules. Copy the flow and session rules from `templates/AGENTS.md` again and keep the project's own rules. `skills/jstack/scripts/template-drift REPO...` checks several repos at once. |
| `warn jstack is the newest version` | The checkout is behind its `origin`. Run `git pull --ff-only && ./install.sh` in the jstack checkout. |
| The agent does not see the skills | The harness reads a different skills folder. Run `./install.sh --target <that folder>`; restart the harness. Check with `ls -l <folder>`: each entry should link into `jstack/skills`. |
| `install.sh` moved a folder to `.jstack-backup-*` | A skill of the same name already existed. Nothing was deleted. Restore it by hand from that folder if you want it back. |
| `removed stale: ...` during install | A jstack link pointed to a skill that was renamed or removed (for example an older name). It is safe. |
| Workers start although quota looks empty | The quota probe has no data, and unknown is not exhaustion. Write `<provider> <account> <percent>` lines to `.jstack/quota.txt` (or set `quota_source`), or set `quota_probe` to a command that follows the contract in `skills/quota-gate/SKILL.md`. |
| Workers never start and report `WAITING` | Every provider in `models` is at 0% in the probe's source, or the source file is older than `quota_max_age_minutes` and a provider is listed at 0. Refresh the file. |
| `pr-wait` never finishes | You passed `--bots` (or set `review_bots`) for a bot that never reviews this repo. Remove it, or add the bot's login to `advisory_bots` so it is reported but not waited for. |
| `pr-wait` says another pid already watches the PR | Use that watcher. Kill it only if its events do not reach you. |
| `pr-wait` or `gh` fail with HTTP 403 or "rate limit" | GitHub's rate limit is used up. `gh api rate_limit --jq .resources.graphql` shows when it resets. |
| A worker stopped early | Check its last report. `WAITING <condition>` means a budget ran out and `fanout` relaunches it when the condition holds. `BLOCKED(...)` names what it needs. A count of attempts is never a reason to stop (`iterate`). |
| A worker keeps failing the same check | Read its `RUNSTATE.md`: the premise it is testing should be written down. If not, `iterate` was not followed. |
| `wave-status` shows `no RUNSTATE.md` | That worktree has no ticket in flight, or the worker has not written its first verdict yet. |
| Settings seem ignored | The block must be a heading `## jstack settings` with `key: value` lines under it. `skills/jstack/scripts/jstack-settings` prints what was resolved; an environment variable `JSTACK_<KEY>` overrides the file. |
