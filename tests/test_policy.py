"""The iteration policy must live in the skills workers actually read, not only in docs.

2026-11-02: docs/OPERATING-MODEL.md said "no fixed attempt cap" while fanout, babysit-pr, full-send and the
AGENTS.md template still said "3 fix attempts"; workers obey the skills and stopped minutes into real work.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SURFACES = [*(ROOT / "skills").glob("*/SKILL.md"), ROOT / "templates/AGENTS.md", ROOT / "templates/CLAUDE.md",
            ROOT / "README.md", ROOT / "AGENTS.md"]
CAP = re.compile(r"(?i)(stop after \d+ fix attempts|after \d+ fix attempts|fix attempts?: *<?n>?/\d+|cap \d\b|"
                 r"\b\d+/3\b|three fix attempts|maximum of \d+ (fix )?attempts)")


def test_no_surface_reintroduces_a_fixed_attempt_cap():
    hits = [(p.relative_to(ROOT).as_posix(), m.group(0)) for p in SURFACES if p.exists()
            for m in CAP.finditer(p.read_text())]
    assert hits == [], f"fixed attempt cap found: {hits}"


def test_iterate_skill_defines_the_loop_and_the_stop_rules():
    text = (ROOT / "skills/iterate/SKILL.md").read_text()
    for needle in ("never a reason to stop", "VERIFIED", "NOT VERIFIED", "INCONCLUSIVE", "premise",
                   "Budgets are not failures", "WAITING", "BLOCKED(env)", "BLOCKED(task)", "BLOCKED(decision)",
                   "plateaus after a pivot", "RUNSTATE.md"):
        assert needle in text, needle


def test_every_surface_that_used_to_cap_points_to_iterate():
    for rel in ("skills/fanout/SKILL.md", "skills/full-send/SKILL.md", "skills/babysit-pr/SKILL.md",
                "templates/AGENTS.md", "docs/OPERATING-MODEL.md"):
        assert "iterate" in (ROOT / rel).read_text(), rel


def test_worker_brief_reports_waiting_for_budgets_not_blocked():
    fanout = (ROOT / "skills/fanout/SKILL.md").read_text()
    assert "WAITING <resume condition>" in fanout
    assert "A budget (quota, rate, time, context) is not a block" in fanout
    assert "BLOCKED(env|task|decision)" in fanout
