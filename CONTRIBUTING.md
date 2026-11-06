# Contributing

1. `make test` must pass: shellcheck, `tools/lint.py` and pytest. `uv run --with pytest python -m pytest -q tests`
   runs the tests alone.
2. **Self-contained.** A skill or doc may name only things this repo ships, plus `git`, `gh` and
   `python3`. Settings go in the `jstack` skill; harness-specific tools go in its actions table
   and nowhere else. Credit to other projects goes in the README and `NOTICE` only. The linter checks this.
3. **One place per rule.** If a rule would live in two files, link to the one.
4. **Behavior over wording.** A new script ships with a test that runs it. A policy that has
   already drifted once gets a test that fails when it drifts again.
5. Smallest change that fixes the case that happened. Prove it on the real artifact.
6. A user-visible change adds a line to `CHANGELOG.md`; a release bumps `VERSION` and is tagged
   `vX.Y.Z`. Copied text keeps its license and gets an entry in `NOTICE`.
