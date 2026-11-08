# jstack

[![ci](https://github.com/lopezsalaberry/jstack/actions/workflows/ci.yml/badge.svg)](https://github.com/lopezsalaberry/jstack/actions/workflows/ci.yml)

A self-contained skill stack for shipping many independent tickets in parallel with coding
agents, without review loops. Plain `skills/<name>/SKILL.md` folders plus a few small tools,
usable from any harness that loads skill folders. Everything a skill needs ships inside this
repo; the only outside requirements are `git`, `gh` and `python3`.

## Quickstart

1. **Prerequisites.** `git`, `python3` 3.9+, and the GitHub CLI signed in (`gh auth login`).
2. **Install.**
   ```sh
   git clone https://github.com/lopezsalaberry/jstack.git ~/jstack
   cd ~/jstack && git checkout v0.9.2      # pin a tag; upstream is never auto-synced
   ./install.sh --dry-run                  # see what it would link
   ./install.sh
   ```
   This links every skill into `~/.agents/skills` and `~/.claude/skills`, plus any
   `--target DIR` you add. Same-name items are moved to `<dir>/.jstack-backup-<timestamp>/`.
   Re-running is safe; `./install.sh --uninstall` removes only jstack links.
3. **Check.** `./install.sh --doctor` says what is missing (`gh` login, settings, links).
4. **Configure the repo you will work in.** Copy `templates/AGENTS.md` into its `AGENTS.md`
   (and `templates/CLAUDE.md` next to it). Set `integration_branch`; leave the rest empty to start.
5. **Run a ticket.** In that repo, tell your agent: *"full send ticket 123 using fanout"*, with the
   ticket's goal and the files it expects to touch. For several tickets, list them all.

Quota gating is off until you give it data: write lines like `claude acct1 63` to
`.jstack/quota.txt` (any script can keep it fresh), or set `quota_probe` to your own command.
Unknown quota never blocks work.

## How it works

```
ready tickets (one ticket = a queue of one)
  └─ fanout ── quota-gate before each launch (launch, switch provider, or pause)
       └─ worker per ticket (no questions, no nested fan-out)
            ticket-start   scope check, worktree from origin/<integration branch>
            full-send      prove (prove-it, verify-<app>, evidence) + per-ticket gate
                           cross-review only if high-risk (1 round)
                           file-pr, babysit-pr (fix-attempt ledger in the PR, no cap)
                           merge when the Merge gate passes, or stop before merge
            report INTEGRATED | READY_FOR_INTEGRATOR | WAITING | BLOCKED(env|task|decision)
```

Principles: parallel by default and limited by quota; one worker per distinct ticket, one
level deep; integrate each green ticket; lean review; evidence from the delivered artifact
before anything is published; budgets, not attempt caps (see `iterate`); measure integrated
merges per day.

## Skills

| Skill | Purpose |
|---|---|
| `jstack` | Settings, harness actions, status words and the `RUNSTATE.md` format every other skill uses; `doctor` |
| `fanout` | Distinct tickets in parallel, one level, quota-limited; `wave-status` shows the wave |
| `groom` | By hand: clean and rank the backlog, check what is ready, offer what to work on; changes nothing without a yes |
| `wrap-up` | The last phase of a wave: validate what the workers reported, ask the operator before merging anything, recap and recommend the next step in one question |
| `ticket-start` | Scope check, then worktree and branch per ticket |
| `quota-gate` | Launch, switch provider or pause from model quota; ships a file-based `quota-probe` |
| `full-send` | Prove, PR, babysit, integrate, or stop before merge; blocks a UI change that leaves the design system |
| `takeover` | Finish or revive someone else's PR, keeping their credit |
| `file-pr` | Open a real PR against the integration branch |
| `babysit-pr` | Drive a PR to green with `pr-wait`; counts fix attempts (no cap) |
| `iterate` | The measured loop that replaces attempt caps: hypothesis, smallest change, verdict, attack the premise, budgets are not failures |
| `cross-review` | One round by an agent that did not write the change: break mode for high-risk changes (findings must be proven by a run), verify mode for user-visible ones (PASS, PASS+NOTES, FAIL) |
| `prove-it` | Verify the real artifact before done; five levels of how sure you are; tests that prove something |
| `evidence` | Local checklist with proof levels, screenshots, before/after output in `.artifacts/`; `proof-valid` says whether a proof still describes the patch |
| `leaving-pr-comments` | How an agent posts PR comments on the user's behalf |
| `create-verify` | Generate a project's `verify-<app>` (it lives in that project) |
| `correct-mistakes` | Turn repeated agent mistakes into checks |

## UI changes

Set `ui_paths` to mark which files are UI. Then the design gate applies twice. When a ticket is
dispatched, `fanout` puts a Design block in its brief and `ticket-start` records a baseline and the
components to reuse; a missing component stops the ticket with `BLOCKED(decision)` instead of being
improvised. When the ticket is proved, `full-send` runs the design check (`token-lint` by default),
compares screenshots with the design source, and the independent verifier checks the design lane too.
A new off-token color, size or font blocks the merge. A tool can prove the tokens, not that the screen
looks like the design, so a visual mismatch also blocks until someone decides.

## Settings

One `## jstack settings` block in the repo's `AGENTS.md`, or `JSTACK_<KEY>` environment
variables. Keys, defaults and precedence: the `jstack` skill. Read the resolved values with
`skills/jstack/scripts/jstack-settings`.

## Stability

Versions are tagged `vX.Y.Z` and every one has a section in [CHANGELOG.md](CHANGELOG.md).
The public surface is: skill names, setting keys and their defaults, the command-line options of
the shipped scripts, the status words, and the `RUNSTATE.md` header lines. While the major version
is 0, a change to any of them is a minor-version bump and is listed under "Changed" or "Removed".
`install.sh` deletes the link of a renamed or removed skill, so an upgrade does not leave dead
entries. CI runs the tests and the linter on Linux and macOS (Python 3.12).

## When something goes wrong

[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md). Iteration policy, quota order and typed
`BLOCKED` states: [docs/OPERATING-MODEL.md](docs/OPERATING-MODEL.md).

## Not included, on purpose

Multi-model panels, arena or best-of races, score-until-perfect loops, formal verification,
principle catalogs, screenshot upload tooling, and platform-specific checks (those belong in
each project's `verify-<app>`).

## Inspired by

jstack is built on ideas and some text from these projects. Exact commits and licenses are in
[NOTICE](NOTICE).

- **tstack** by Theo Browne, [t3dotgg/tstack](https://github.com/t3dotgg/tstack): the pull-request
  lifecycle (`full-send`, `file-pr`, `babysit-pr`, `leaving-pr-comments`, the `pr-wait` watcher) and
  the practice of cross-model review.
- **pstack** by Cursor, [cursor/plugins](https://github.com/cursor/plugins/tree/main/pstack): the
  hypothesis loop and verdicts behind `iterate`, `prove-it` and its proof levels, `create-verify`,
  `correct-mistakes`, the fan-out pattern, and, from its shipping and babysit playbooks, the
  independent verifier, the proof that follows the patch, the red-CI triage and the decision trail.
- **rstack** by Michael Shimeles, [michaelshimeles/rstack](https://github.com/michaelshimeles/rstack):
  the ticket-start steps and the evidence protocol.

## Development

`make test` runs shellcheck, the repo linter (`tools/lint.py`) and pytest. The linter fails if a
skill or doc names another project, references a skill the repo does not ship, or lacks
frontmatter. CI (`.github/workflows/ci.yml`) runs the same. See [CONTRIBUTING.md](CONTRIBUTING.md),
[SECURITY.md](SECURITY.md) and [CHANGELOG.md](CHANGELOG.md).

## License

MIT for original files. Copied material keeps its license; see [NOTICE](NOTICE).
