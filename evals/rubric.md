# Rubric

Score each project 1 to 10 on each criterion. Use only evidence you can cite
(`file:line`, a command and its output, or an `EVIDENCE.json` fact). Volume is
not quality: padding, duplicate rules and unused files count against
"focus", never for "scope". A score of 7 or more needs at least two cited pieces
of evidence. If a claim in a README is not backed by a file or a test, it does
not count.

Anchors, the same for every project:

| Score | Meaning |
|---|---|
| 1-3 | Absent, broken, or contradicted by the repo |
| 4-6 | Present but partial, undocumented, or dependent on things the project does not ship |
| 7-8 | Works as documented for a new user without private knowledge; gaps are minor |
| 9-10 | Exemplary: demonstrably tested, documented and hard to misuse |

## Criteria

1. **scope** - How much of the work of shipping a code change with agents it covers
   (investigate, change, prove, review, PR, merge, resume). 7 = the whole path from
   ticket to merged change, including stopping before merge and taking over someone
   else's or an old PR; 4 = a part of the path.
2. **focus** - Simplicity and lack of redundancy. Counterweight to scope. 7 = every
   skill earns its place, rules live in one place, a new user can read the core in an
   hour; 4 = overlapping skills or rules that contradict each other.
3. **originality** - Ideas or mechanisms that are not copied or lightly adapted
   from another project. Judge only what the repo itself shows (source lines,
   NOTICE, commit messages). 7 = at least two mechanisms with their own design that
   solve a real problem; 4 = mostly adaptation.
4. **parallel** - Running many independent tickets at once. 7 = a defined
   dispatcher, conflict rules between tickets, who relaunches a stalled worker,
   and a final report; 4 = one ticket at a time.
5. **quota** - Handling subscription or rate limits, pause and resume. 7 = a
   shipped probe or documented contract, a fallback order, an observable resume
   condition, and budgets kept distinct from failures; 4 = mentions limits only.
6. **proof** - Verification before done. 7 = requires evidence from the real
   artifact, defines what counts as proof, and keeps it where a reviewer can see
   it; 4 = "run the tests".
7. **crossreview** - Independent review by a different model or agent. 7 =
   defined trigger, brief, a rule for findings the reviewer cannot prove, and a
   fallback when the other model is unavailable; 4 = optional review with no rules.
8. **portability** - Works across agent harnesses and models without edits.
   7 = harness-specific tools and model ids are isolated behind one documented
   mapping or variables, with a fallback for each; 4 = names one harness' tools or
   fixed model ids throughout the skills.
9. **tests** - Automated checks of the project itself. 7 = tests that exercise
   behavior (not only wording) for each shipped tool, plus CI that runs them;
   4 = linting or text checks only.
10. **docs** - A new user can install, run a first task and fix a common failure
    from the docs alone. 7 = quickstart, concept map, troubleshooting, no stale
    references; 4 = a README that lists parts.
11. **adoption** - Time and knowledge needed before the first real use. 7 = a
    working install in at most five documented steps, a check command that says
    what is missing, and no undefined variables or unshipped components;
    4 = needs private setup that the repo does not provide.
12. **guardrails** - Safe autonomy. 7 = explicit limits on merge, force-push and
    deletes, a way to stop before merge, typed stop states, and no bypass of branch
    protection; 4 = autonomy granted with few limits.
13. **drift** - Resistance to the docs and skills disagreeing over time.
    7 = a mechanism that fails when they disagree (a test or lint that checks
    behavior or consistency across files) and pinned provenance; 4 = manual care.
14. **maturity** - How safe it is to depend on. Age alone is not scored.
    7 = tagged releases with a changelog, passing CI on the default branch, a
    contribution and security policy, and a history showing fixes made after real
    use; 9-10 adds months of history and outside contributors.

## Output

One JSON object (see `brief.md`). Do not average. Do not round up.
