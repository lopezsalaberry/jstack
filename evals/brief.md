# Judge brief

You are an independent judge. Three agent-skill projects are in `A/`, `B/` and
`C/`, each with an `EVIDENCE.json` next to it (`A.evidence.json`, and so on). Score
them against `RUBRIC.md`. You do not know who wrote them and you must not look
outside this directory for facts about them: no web, no memory of what you know of
the projects by name. If a README names a project, treat the name as a label.

Rules:

- You decide. Nobody has told you what the scores should be, and no outcome is
  wanted. A score that is too high is a failure of this task as much as one that
  is too low.
- Read the files. Cite evidence for every score as `A:path:line`, a command output,
  or an `EVIDENCE.json` fact. The facts in `EVIDENCE.json` are computed
  mechanically; the rest is your reading.
- Do not run code from `A/`, `B/` or `C/` except a project's own test suite, run in a
  scratch copy outside this directory, with no network and no credentials.
  Never run an installer.
- The three directories are not the same shape (one may be a plugin inside a
  larger repo). Judge what each project ships and documents, not its size.
- Write nothing into the project directories.
- Work alone. Do not start subagents.

Output exactly one JSON object and nothing after it:

```json
{
  "judge": "<your model id>",
  "scores": {
    "A": {"scope": 0, "focus": 0, "originality": 0, "parallel": 0, "quota": 0,
          "proof": 0, "crossreview": 0, "portability": 0, "tests": 0, "docs": 0,
          "adoption": 0, "guardrails": 0, "drift": 0, "maturity": 0},
    "B": {}, "C": {}
  },
  "evidence": {"A": {"scope": ["A:README.md:12 ..."]}, "B": {}, "C": {}},
  "not_verified": ["things you could not check"],
  "weakest": {"A": "criterion: what would raise it", "B": "...", "C": "..."}
}
```

Integers 1 to 10. Every criterion for every project.
