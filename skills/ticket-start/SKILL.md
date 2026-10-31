---
name: ticket-start
description: "Start a ticket in its own git worktree and branch from the project's integration branch, after checking open PRs and other worktrees for overlap. Use before any edit for a ticket. Read-only work does not need it."
---

> Adapted from [michaelshimeles/rstack](https://github.com/michaelshimeles/rstack) `new-feature` @ `11b15767d7587bab11f6c4957507b5f26d1785c7`: integration branch per project, other worktrees included in the scope check.

# Ticket start

Each ticket gets its own worktree and branch. Never edit the integration
branch directly and never reuse another ticket's worktree.

1. **Existing isolation.** Check `git worktree list`, `git status --short`,
   and the branch. If this ticket already has a worktree, use it and skip to step 6.
2. **Sync.** `git fetch origin`.
3. **Scope check.** Run `gh pr list` and skim open PRs' files
   (`gh pr diff <n> --name-only`), and `git -C <wt> status --short` plus
   `git -C <wt> diff --name-only origin/<integration branch>...` for each other
   worktree.
4. **Name.** Lowercase with hyphens plus a short unique suffix, for example
   `user-auth-0816a`. If the name exists, pick another; never force or reuse.
5. **Create.** `git worktree add <worktrees-dir>/<name> -b <prefix>/<name> origin/<integration branch>`.
   Use a directory outside the checkout or a gitignored one.
6. **Enter and verify.** `git branch --show-current` prints the ticket
   branch. Install dependencies inside the worktree only when the checks need them.
7. **Clean up** after integration (the worker that integrated): `git worktree remove <path>` and
   `git branch -D <prefix>/<name>`. `-D` is expected: after a squash or rebase
   merge, `-d` refuses even though the work is merged.

## Remember

- Worktrees do not isolate dev-server ports or shared databases. Confirm a
  port answers your process before trusting what it serves.
- Resolve lockfile conflicts by regenerating, never by hand-merging.
