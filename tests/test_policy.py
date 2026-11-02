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
                   "plateaus", "RUNSTATE.md", "Per-iteration brake", "JSTACK_ITER_MINUTES",
                   "JSTACK_QUOTA_PROBE", "stagnation, not attempts", "observable",
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
