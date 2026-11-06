---
name: prove-it
description: "Apply after completing a task, before declaring done. Verify against the real artifact (run the feature, read the actual value, inspect the diff), not a proxy, self-report, or 'it compiles.'"
---

# Prove It Works

Verify every task output by checking the real thing directly. Do not infer from proxies, self-reports, or "it compiles."

**Why:** Unverified work has unknown correctness. Indirect verification (file mtimes, output freshness, agent self-reports, cached screenshots) feels cheaper than direct observation. Acting on a wrong inference costs far more than checking the source.

Check the real thing, not a proxy:
- Check process liveness directly, not indirectly through derived state
- Read the actual value, not a cached or derived representation
- When verification fails, suspect the observation method before suspecting the system
- For anything delivered to someone else, check the delivered artifact itself, not the build tree it came from

## Script the check when you can

The strongest proof is a deterministic script that re-runs the same comparison, not a one-time eyeball. Write the script, run it, and keep its output as an artifact a reviewer can re-run instead of trusting your word.

Keep the artifact visible for the human. Commit it only for large or complex work where the trail has to be auditable later, like a big port or migration.

## How sure are you

Say how far down this list each claim got, and never report a higher level than you reached.

1. **You said so.** Worthless on its own.
2. **You pointed at the line.** A real `file:line`, or the library's own source.
3. **You walked the failing case** through the code and showed it cannot happen.
4. **You ran it.** A script or test that calls the real code and fails loudly if you are wrong.
5. **You reproduced it** in the running, delivered artifact.

A claim is `PASS` at level 4 or 5. Below that it is "unproven (level N)" and is written that way.

For a risky change, do not hand back a convincing write-up. Find the one fact the change is safe
because of (for example "this call only drops entries that are already dead"), prove that fact at
level 4 or higher, and paste what happened. If you could not, write `unproven`.

## A test that proves something

Judge each test you write or keep against two imagined edits:

- **Break the behavior** (return a wrong value, skip an effect, do it twice). If the test still
  passes, it proves nothing.
- **Change only the internals**, keeping every observable result. If the test now fails, it is
  pinned to the implementation and will need rewriting on every refactor.

Keep a test that catches the first and survives the second. Prefer no new test to a bad one.
Never change a test just to match a wrong implementation.
