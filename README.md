# jstack

[![ci](https://github.com/lopezsalaberry/jstack/actions/workflows/ci.yml/badge.svg)](https://github.com/lopezsalaberry/jstack/actions/workflows/ci.yml)

A small skill stack for shipping tickets with coding agents: every change is proven on the real
thing, shown to whoever reads the pull request, looked at by someone who did not write it when it
matters, and merged without review loops. Five `skills/<name>/SKILL.md` folders and a few small
tools, usable from any harness that loads skill folders. The only outside requirements are `git`,
`gh` and `python3`.

## Quickstart

1. **Prerequisites.** `git`, `python3` 3.9+, and the GitHub CLI signed in (`gh auth login`).
2. **Install.**
   ```sh
   git clone https://github.com/lopezsalaberry/jstack.git ~/jstack
   cd ~/jstack && ./install.sh --dry-run   # see what it would link
   ./install.sh
   ```
   This links the skills into `~/.agents/skills` and `~/.claude/skills`, plus any `--target DIR`.
   A same-name item is moved to `<dir>/.jstack-backup-<timestamp>/`. Re-running is safe;
   `./install.sh --uninstall` removes only jstack links.
3. **Give your agents the rules card.** Agents follow a rule only if they read it, so the eight
   rules live in one short block. Put it where your harness always looks:
   `./install.sh --card <repo>/AGENTS.md` for one repo (or copy `templates/AGENTS.md`, which also
   has the settings block), or `--card` with the file your harness loads for every repo.
4. **Check.** `./install.sh --doctor` says what is missing (`gh` login, the card, settings, links).
5. **Run a ticket.** Tell your agent: *"full send ticket 123"*, with the ticket's goal, the files it
   expects to touch and what must be true when it is done. For several tickets, list them all.

Quota gating is off until you give it data: write lines like `claude acct1 63` to
`.jstack/quota.txt`, or set `quota_probe` to your own command. Unknown quota never blocks work.

## How it works

```
the rules card              eight rules, in a file every session reads
wave                        one worker per ticket; `brief` writes each brief and makes you name the model
  └─ ticket                 own worktree and branch → proof (`checklist-init`, levels 1 to 5)
       │                    → pull request with a Before / After table (`publish`)
       ├─ review            one round by someone else, for high-risk or user-visible changes
       └─ check             the merge gate as one command; the worker pastes it, the orchestrator reruns it
wave, when it drains        validate, decide, recap, ONE recommendation in ONE question
status                      INTEGRATED | READY_FOR_INTEGRATOR | WAITING | BLOCKED(env|task|decision)
```

A rule goes where it is sure to be followed: in a script when a command can check it, in the card
when every session must know it, and in a skill only for what is left. `tests/test_budget.py` fails
when the skills grow past a word budget, so a new paragraph has to replace an old one.

## Skills

| Skill | Purpose |
|---|---|
| `jstack` | Reference: the rules card, settings, harness actions, status words, `RUNSTATE.md`; `doctor` |
| `ticket` | One ticket from the first edit to the merged PR: worktree, proof, PR, `check`, merge. Tools: `checklist-init`, `proof-valid`, `token-lint`, `publish`, `check` |
| `review` | One round by an agent that did not write the change: break mode for high-risk changes, verify mode for user-visible ones |
| `wave` | Several tickets at once, quota and model choice, and the close: validate, recap, recommend. Tools: `brief`, `quota-probe`, `wave-status` |
| `groom` | By hand: clean and rank the backlog and offer what to work on; changes nothing without a yes |

`extras/` holds five more that are not installed by default (`./install.sh --extras`): `babysit-pr`
with the `pr-wait` watcher for harnesses that cannot watch a PR, `takeover`, `leaving-pr-comments`,
`create-verify` and `correct-mistakes`.

## UI changes

Set `ui_paths` to mark which files are UI. Then `brief` adds a design block to the worker's brief,
the worker captures each screen before and after, `check` runs the design check (the shipped
`token-lint` by default: no new color, size or font outside the design tokens) and refuses a pull
request that shows no picture. A tool can prove the tokens, not that a screen looks like the design,
so a mismatch the worker cannot resolve stops as `BLOCKED(decision)`.

## Settings

Nine keys. A repo's values go in a `## jstack settings` block of its `AGENTS.md`; the operator's own
go in `~/.config/jstack/settings` for every repo on the machine; `JSTACK_<KEY>` overrides both. Keys
and defaults: the `jstack` skill. `skills/jstack/scripts/jstack-settings` prints what was resolved.

## Stability

Versions are tagged `vX.Y.Z` and each has a section in [CHANGELOG.md](CHANGELOG.md). The public
surface is the skill names, the setting keys and defaults, the options of the shipped scripts, the
status words, the rules card and the `RUNSTATE.md` header lines. `install.sh` deletes the link of a
renamed or removed skill. CI runs the tests and the linter on Linux and macOS.

## When something goes wrong

[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Not included, on purpose

Multi-model panels, best-of races, score-until-perfect loops, formal verification, principle
catalogs, a hosted upload service (the pictures of a pull request live in a ref of the repo itself)
and platform-specific checks (those belong in each project's `verify-<app>`).

## Inspired by

jstack is built on ideas and some text from these projects. Exact commits and licenses are in
[NOTICE](NOTICE).

- **tstack** by Theo Browne, [t3dotgg/tstack](https://github.com/t3dotgg/tstack): the pull-request
  lifecycle behind `ticket` and `babysit-pr`, `leaving-pr-comments`, the `pr-wait` watcher and the
  practice of cross-model review. The Before / After evidence table, "Not shown" and "Who did the
  work" follow the pull requests of [pingdotgg/t3code](https://github.com/pingdotgg/t3code).
- **pstack** by Cursor, [cursor/plugins](https://github.com/cursor/plugins/tree/main/pstack): the
  hypothesis loop and the proof levels in `ticket`, `create-verify`, `correct-mistakes`, the fan-out
  pattern and the orchestrator that runs the program and not the code in `wave`, the independent
  verifier, the proof that follows the patch and the red-CI triage.
- **rstack** by Michael Shimeles, [michaelshimeles/rstack](https://github.com/michaelshimeles/rstack):
  the ticket start steps and the evidence protocol.

## Development

`make test` runs shellcheck, the repo linter (`tools/lint.py`) and pytest. The linter fails if a
skill or doc names another project, references a skill the repo does not ship, or lacks
frontmatter. CI (`.github/workflows/ci.yml`) runs the same. See [CONTRIBUTING.md](CONTRIBUTING.md),
[SECURITY.md](SECURITY.md) and [CHANGELOG.md](CHANGELOG.md).

## License

MIT for original files. Copied material keeps its license; see [NOTICE](NOTICE).
