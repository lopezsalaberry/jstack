# jstack

A lean, agent-agnostic skill stack for shipping many independent tickets in
parallel without review loops. Plain `skills/<name>/SKILL.md` folders plus a
few small tools, usable from Claude Code, Codex, Cursor, Hermes, T3 Code, or
any harness that loads skill folders.

Rules are written inside each skill. The only per-project setting is the
integration branch, named in each repo's `AGENTS.md`. See [AGENTS.md](AGENTS.md).

## Principles

- **Parallel by default, limited by quota.** No fixed worker count. Pause at
  0%, never switch to another model.
- **One worker per distinct ticket, one level deep.** No races, no best-of.
- **Integrate per green ticket** into the project's integration branch. The
  wave's full build runs separately and never blocks.
- **Lean review.** Self-validation with real evidence. Cross-model review only
  for high-risk changes, 1 round.
- **Evidence from the delivered artifact before anything is published.**
- **Hard caps.** 3 fix attempts per ticket, then block and escalate.
- **Measure integrated merges per day.**

## End-to-end flow

```
ready tickets from the project's tracker (one ticket = queue of one)
  └─ fanout ── quota-gate before each launch (launch or pause)
       └─ worker per ticket (no questions, no nested fan-out)
            ticket-start   scope check (open PRs, other worktrees), worktree from origin/<integration branch>
            full-send      verify-<app> + evidence + prove-it + per-ticket gate
                           sol-loop only if high-risk (1 round)
                           file-pr, babysit-pr (fix-attempt ledger in the PR, cap 3)
                           merge when the Merge gate passes
            report INTEGRATED | BLOCKED
```

## Skills

### Loop

| Skill | Origin | Purpose |
|---|---|---|
| `fanout` | adapted from pstack `swarm` | Distinct tickets in parallel, one level, quota-limited |
| `ticket-start` | adapted from rstack `new-feature` | Scope check, then worktree and branch per ticket |
| `quota-gate` | new | Launch or pause from model quota |
| `sol-loop` | adapted from tstack | One-round cross-model review, high-risk only |
| `full-send` | adapted from tstack | Prove, PR, babysit, integrate, with lean review and fix cap |
| `file-pr` | adapted from tstack | Open a real PR against the integration branch |
| `babysit-pr` | tstack | Drive a PR to green with `pr-wait`; defines and counts fix attempts |
| `leaving-pr-comments` | tstack | How to post PR comments |
| `prove-it` | pstack `principle-prove-it-works` | Verify the real artifact before done |
| `evidence` | adapted from rstack `evidence-driven-testing` | Local checklist, screenshots, optional video in `.artifacts/`, summary in the PR |

### Setup and maintenance

| Skill | Origin | Purpose |
|---|---|---|
| `create-verify` | pstack `create-verification-skill` | Generate a project's `verify-<app>` (lives in that project) |
| `correct-mistakes` | pstack `correct` | Turn repeated agent mistakes into checks |

Requires git and `gh`.

## Install

0. **Quota probe.** Set `JSTACK_QUOTA_PROBE` on each machine. While it is unset,
   `quota-gate` starts nothing. Example output, one line per account:

   ```
   account-1 63
   account-2 0
   ```

1. **Skills.**

With the [`skills` CLI](https://skills.sh):

```sh
npx skills add lopezsalaberry/jstack
```

Or from a pinned clone:

```sh
git clone https://github.com/lopezsalaberry/jstack.git ~/base/jstack
cd ~/base/jstack && git checkout <tag>
./install.sh --dry-run
./install.sh --target ~/.hermes/skills
```

Links every skill into `~/.agents/skills` (Codex, Cursor, and others) and
`~/.claude/skills` (Claude Code), plus any `--target` dir. T3 Code
threads use the dirs of the harness they run.
Same-name items are moved to
`<dir>/.jstack-backup-<timestamp>/`. Re-running is safe.

`./install.sh --uninstall` removes only jstack links. Backups stay in place to
restore by hand.

2. **Each work repo.** Copy `templates/AGENTS.md` into the repo's `AGENTS.md`
   (the end-to-end flow, including when not to use it) and `templates/CLAUDE.md`
   (`@AGENTS.md`) next to it.

Pin a tag. Upstream changes are pulled by hand and reviewed, never auto-synced.

## Development

`make test` runs shellcheck, the repo linter (`tools/lint.py`), and pytest. CI
(`.github/workflows/ci.yml`) runs the same.

## Not included, on purpose

Council and multi-model panels, arena/best-of races, reflect, greploop
(score-until-perfect loops), formal verification, principle catalogs, and
platform-specific checks (those belong in each project's `verify-<app>`),
and screenshot upload tooling.

## License

MIT for original files. Copied material keeps its license; see [NOTICE](NOTICE).
