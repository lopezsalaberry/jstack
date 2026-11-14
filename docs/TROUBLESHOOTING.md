# Troubleshooting

Start with `./install.sh --doctor`. It prints one line per check (`ok`, `warn`, `FAIL`) and
exits 1 on a `FAIL`.

| Symptom | Cause and fix |
|---|---|
| `FAIL gh` or `FAIL gh authenticated` | The GitHub CLI is missing or signed out. Install it from https://cli.github.com, then `gh auth login`. |
| `warn rules card` | No file an agent reads carries the current card, so the rules are not followed. `./install.sh --card <file>` writes it into a repo's `AGENTS.md` or into the file your harness loads for every repo, and replaces an older one. |
| `warn UI design gate: OFF` | The repo has design tokens but no `ui_paths`, so no change counts as a UI change and the design check never runs. Add `ui_paths: <globs of the UI files>` to the `## jstack settings` block. |
| `warn settings this version does not read` | The `## jstack settings` block has keys from an older version. Remove them. |
| `warn jstack is the newest version` | The checkout is behind its `origin`. Run `git pull --ff-only && ./install.sh` in the jstack checkout. |
| The agent does not see the skills | The harness reads a different skills folder. Run `./install.sh --target <that folder>` and restart the harness. Each entry of the folder should link into `jstack/skills`. |
| `install.sh` moved a folder to `.jstack-backup-*` | A skill of the same name already existed. Nothing was deleted; restore it by hand if you want it back. |
| `removed stale: ...` during install | A jstack link pointed to a skill that was renamed or removed. It is safe. |
| `check` says `FAIL proof` | Read the reason on the line. "Records no patch": run `proof-valid --stamp` once the proof is final. "The patch changed": the change was edited after it was proven; prove it again, then stamp. Never edit the checklist only to make the line pass. |
| `check` says `FAIL screenshot` | A UI change and the PR shows no picture. A path under `.artifacts/` is not one: that folder is not in git. Name the files `before-<state>.png` and `after-<state>.png` and run `publish <ticket> --pr <number>`. |
| `publish` exits 2 | Too many files, a file over the size limit, or an `origin` that is not on GitHub. It names which. Keep the few files that carry the proof; for a non-GitHub origin show the pictures in your message. |
| `check` fails on a CI job that never ran | A job that ran no step is neither a pass nor a failure. Say so next to the pasted output and rest on your own run. |
| Workers start although quota looks empty | The probe has no data, and unknown is not exhaustion. Write `<provider> <account> <percent>` lines to `.jstack/quota.txt`, or set `quota_probe` to a command that answers `--provider <name>` with exit 0, 1 or 2. |
| Workers never start and report `WAITING` | Every provider the harness can start is at 0% or marked exhausted. `quota-probe --provider <name>` says which; `--clear <name>` removes a mark that no longer holds. |
| A refused provider is tried again after an hour | Its mark lasts 60 minutes by default and the refusal lasts longer, for example a monthly cap. Mark it with `--until <date or date-time>`. |
| A review stopped to ask which provider to use | A note or instruction fixed one provider. Put the order in `reviewer_models` (the operator's `~/.config/jstack/settings` covers every repo) and delete the note. |
| Every worker runs on the strongest model | A delegate that names no model inherits its parent's. Write each brief with `brief`, which will not run without `--model` and `--effort`. |
| A worker stopped early | Read its last line. `WAITING <condition>` means a budget ran out and `wave` relaunches it when the condition holds. `BLOCKED(...)` names what it needs. |
| `wave-status` shows `no RUNSTATE.md` | That worktree has no ticket that stopped early: `RUNSTATE.md` is written only when a worker stops before the end. |
| `pr-wait` never finishes | You passed `--bots` for a bot that never reviews this repo. Remove it, or pass it to `--advisory-bots`. |
| Settings seem ignored | The block must be a heading `## jstack settings` with `key: value` lines under it. `jstack-settings` prints what was resolved; `JSTACK_<KEY>` overrides the repo, and the repo overrides `~/.config/jstack/settings`. |
