"""The skills have a word budget. Text that every worker loads is paid for in every session, and it grew from 8,600 to
13,200 words in eight days without anyone deciding it should. A new paragraph has to replace an old one."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOTAL = 5200        # the five skills together
PER_SKILL = 1700    # the longest one a worker loads
words = lambda path: len(path.read_text().split())


def test_the_skills_stay_inside_their_word_budget():
    sizes = {p.parent.name: words(p) for p in sorted((ROOT / "skills").glob("*/SKILL.md"))}
    assert set(sizes) == {"groom", "jstack", "review", "ticket", "wave"}, "a new skill is a decision, not a habit"
    over = {name: n for name, n in sizes.items() if n > PER_SKILL}
    assert not over, f"over {PER_SKILL} words: {over}. Cut before you add"
    assert sum(sizes.values()) <= TOTAL, f"the skills are {sum(sizes.values())} words, budget {TOTAL}: cut before you add"
