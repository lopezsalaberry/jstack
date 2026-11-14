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
| Workers never start and report `WAITING` | Every provider the harness can start (or every one in `models`, when it is set) is at 0% in the probe's source or is marked exhausted. `quota-probe --provider <name>` says which; `--clear <name>` removes a mark that no longer holds. |
| A refused provider is tried again after an hour | Its mark was set with `--minutes` (60 by default) but the refusal lasts longer, for example a monthly cap. Mark it with `--until <date or date-time>` using the reset the refusal names. |
| A PR says the screenshots are under `.artifacts/` | That folder is not in git, so the reader sees nothing. Run `skills/evidence/scripts/publish <ticket> --pr <number>`; it needs a GitHub `origin` (otherwise it lists the files and exits 2) and permission to push `refs/jstack-evidence/<ticket>`. More than 8 files is refused: name the few that carry the proof. `pr-evidence-check --pr <number>` says whether the PR now shows a picture. |
| A review stopped to ask which provider to use | A note or instruction fixed one provider and the agent obeyed it over `reviewer_models`. Put the order in `reviewer_models` (the operator's file `~/.config/jstack/settings` covers every repo) and delete the note. |
| Every worker runs on the strongest model | A delegate that names no model inherits its parent's. Orchestrator and workers must be told apart: see "Pick the model" in `skills/quota-gate/SKILL.md`. |
| `pr-wait` never finishes | You passed `--bots` (or set `review_bots`) for a bot that never reviews this repo. Remove it, or add the bot's login to `advisory_bots` so it is reported but not waited for. |
| `pr-wait` says another pid already watches the PR | Use that watcher. Kill it only if its events do not reach you. |
| `pr-wait` or `gh` fail with HTTP 403 or "rate limit" | GitHub's rate limit is used up. `gh api rate_limit --jq .resources.graphql` shows when it resets. |
| A worker stopped early | Check its last report. `WAITING <condition>` means a budget ran out and `fanout` relaunches it when the condition holds. `BLOCKED(...)` names what it needs. A count of attempts is never a reason to stop (`iterate`). |
| A worker keeps failing the same check | Read its `RUNSTATE.md`: the premise it is testing should be written down. If not, `iterate` was not followed. |
| `wave-status` shows `no RUNSTATE.md` | That worktree has no ticket in flight, or the worker has not written its first verdict yet. |
| Settings seem ignored | The block must be a heading `## jstack settings` with `key: value` lines under it. `skills/jstack/scripts/jstack-settings` prints what was resolved; an environment variable `JSTACK_<KEY>` overrides the file, and the repo's block overrides `~/.config/jstack/settings`. |
