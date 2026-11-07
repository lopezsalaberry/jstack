"""The iteration policy must live in the skills workers actually read, not only in docs.

2026-11-02: docs/OPERATING-MODEL.md said "no fixed attempt cap" while fanout, babysit-pr, full-send and the
AGENTS.md template still said "3 fix attempts"; workers obey the skills and stopped minutes into real work.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
SURFACES = [*SKILLS, ROOT / "templates/AGENTS.md", ROOT / "templates/CLAUDE.md", ROOT / "README.md",
            ROOT / "AGENTS.md", ROOT / "docs/OPERATING-MODEL.md"]
CAP = re.compile(
    r"(?i)(\b(max(imum)?|up to|at most|after|stop after|limit(ed)? to)\s+(\d+|one|two|three|four|five)\s+(fix(es)? )?"
    r"(attempts?|tries|retries)\b"
    r"|fix attempts?:\s*[<\w]+>?\s*/\s*\d+|\b\d+\s*fix attempts?\b|\bcap\s+(of\s+)?\d+\s+(fix )?attempts?\b"
    r"|fix[- ]attempt cap(?!\))|\bwhen the cap is used up\b)")
# The docs quote the old rule once, as history, to explain what was replaced.
HISTORICAL = ('"3 fix attempts, then block"', 'still said "3 attempts"', 'old "3 fix attempts" cap')
STATUSES = ("INTEGRATED", "READY_FOR_INTEGRATOR", "WAITING", "BLOCKED(env|task|decision)")


def hits(path):
    text = path.read_text()
    for quote in HISTORICAL:
        text = text.replace(quote, "")
    return [m.group(0) for m in CAP.finditer(text)]


def test_no_surface_reintroduces_a_fixed_attempt_cap():
    found = {p.relative_to(ROOT).as_posix(): hits(p) for p in SURFACES if p.exists() and hits(p)}
    assert found == {}, f"fixed attempt cap found: {found}"


def test_the_cap_detector_catches_the_old_wording_and_ignores_legit_text():
    for old in ("Stop after 3 fix attempts.", "Fix attempts: <n>/3", "After 3 fix attempts, do not push",
                "retry up to 3 times is fine? max 5 attempts", "cap 3 fix attempts", "when the cap is used up"):
        assert CAP.search(old), old
    for legit in ("parallel batches by file set (cap, 429 backoff)", "1/3 of the tickets", "Fix attempts: <n>",
                  "a count of stagnation, never of attempts", "iterations run (a count, never a cap)"):
        assert not CAP.search(legit), legit


def test_iterate_skill_defines_the_loop_the_brakes_and_the_stop_rules():
    text = (ROOT / "skills/iterate/SKILL.md").read_text()
    for needle in ("never a reason to stop", "VERIFIED", "NOT VERIFIED", "INCONCLUSIVE", "premise",
                   "Budgets are not failures", "WAITING", "BLOCKED(env)", "BLOCKED(task)", "BLOCKED(decision)",
                   "plateaus", "RUNSTATE.md", "Per-iteration brake", "iteration_minutes",
                   "quota-gate", "stagnation, not attempts", "observable",
                   "Two consecutive `INCONCLUSIVE`"):
        assert needle in text, needle


def test_every_surface_that_used_to_cap_points_to_the_iterate_skill():
    for rel in ("skills/fanout/SKILL.md", "skills/full-send/SKILL.md", "skills/babysit-pr/SKILL.md",
                "templates/AGENTS.md", "docs/OPERATING-MODEL.md"):
        assert "`iterate`" in (ROOT / rel).read_text() or "skills/iterate" in (ROOT / rel).read_text(), rel
    assert "`iterate`" in (ROOT / "README.md").read_text()


def test_status_vocabulary_is_the_same_in_iterate_fanout_and_readme():
    for rel in ("skills/iterate/SKILL.md", "skills/fanout/SKILL.md", "README.md"):
        text = (ROOT / rel).read_text()
        for status in ("INTEGRATED", "READY_FOR_INTEGRATOR", "WAITING", "BLOCKED"):
            assert status in text, (rel, status)
    assert "BLOCKED(env|task|decision)" in (ROOT / "skills/fanout/SKILL.md").read_text()
    assert "BLOCKED(env|task|decision)" in (ROOT / "README.md").read_text()


def test_waiting_has_an_owner_in_fanout():
    fanout = (ROOT / "skills/fanout/SKILL.md").read_text()
    assert "`WAITING <condition>` is\n   parked, not done" in fanout
    assert "relaunch ONE fresh worker for the same\n   ticket" in fanout
    assert "dies without reporting" in fanout
    assert "WAITING <resume condition>" in fanout
    assert "A budget (quota, rate, time, context) is not a block" in fanout


def test_waiting_is_never_conflated_with_blocked_for_budgets():
    text = (ROOT / "skills/iterate/SKILL.md").read_text()
    assert "Never report `BLOCKED` for a budget" in text
    assert "report `WAITING`" in text


def test_new_skill_is_listed_and_installable():
    assert "| `iterate` |" in (ROOT / "README.md").read_text()
    assert (ROOT / "skills/iterate/SKILL.md").exists()
    notice = (ROOT / "NOTICE").read_text()
    assert "iterate" in notice and "figure-it-out" in notice


def test_the_template_carries_the_session_rules():
    """0.8.0: these rules live in the file every repo reads, not only in the groom skill. Each token must
    sit on its own rule's line: a token that survives somewhere else does not keep the rule."""
    lines = (ROOT / "templates/AGENTS.md").read_text().splitlines()
    rules = {
        "2. Queue =": ("`Touches:`", "`Done when:`", "`groom`"),
        "7. A user-visible ticket": ("`INTEGRATED`", "review", "not to done"),
        "- A decision": ("product doc",),
        "- At the start": ("`wave-status`", "`WAITING`"),
    }
    for start, tokens in rules.items():
        found = [line for line in lines if line.startswith(start)]
        assert len(found) == 1, f"templates/AGENTS.md must have exactly one rule starting {start!r}"
        for token in tokens:
            assert token in found[0], f"rule {start!r} lost {token}"


def test_groom_never_sends_delivered_work_to_canceled():
    """0.8.1: the first run found merged tickets; groom had listed 'already on the integration branch' as a cancel reason."""
    text = (ROOT / "skills/groom/SKILL.md").read_text()
    cancel = next(line for line in text.splitlines() if "CANCEL only with evidence" in line)
    assert "integration branch" not in cancel, "merged work is DELIVERED, not a reason to cancel"
    delivered = next(line for line in text.splitlines() if line.strip().startswith("- DELIVERED"))
    assert "never to canceled" in text and "merge-base --is-ancestor" in text and delivered


def test_a_silent_start_is_a_refusal_in_quota_gate_and_cross_review():
    """2026-11-07: a review started on an account in a quota cooldown produced nothing for seven hours. No error ever
    said it had refused, so nothing was marked and nothing moved on to the next candidate."""
    gate = (ROOT / "skills/quota-gate/SKILL.md").read_text()
    paragraph = gate.split("**Silence is a refusal.**")[1].split("\n\n")[0]
    assert "10 minutes" in paragraph and "--mark-exhausted" in paragraph
    assert "**Any other exit is a broken probe, not data.**" in gate
    review = (ROOT / "skills/cross-review/SKILL.md").read_text()
    step = review.split("3. **Try it.**")[1].split("4. **Independence ladder.**")[0]
    assert "10 minutes" in step and "silent" in step
