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
        "- When a wave drains": ("`wrap-up`",),
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
    assert "nothing 2 minutes later" in paragraph and "10 minutes" not in paragraph and "--mark-exhausted" in paragraph
    assert "**Any other exit is a broken probe, not data.**" in gate
    fresh = " ".join(gate.split("**A reading is for this launch only.**")[1].split("\n\n")[0].split())
    assert "Run the probe again before every launch" in fresh and "is not data" in fresh and "earlier in the session" in fresh
    review = (ROOT / "skills/cross-review/SKILL.md").read_text()
    step = " ".join(review.split("3. **Try it.**")[1].split("4. **Independence ladder.**")[0].split())
    assert "wait at most 2 minutes" in step and "those 2 minutes" in step and "10 minutes" not in step and "silent" in step


def test_wrap_up_validates_before_it_recommends_and_asks_once():
    """0.9.0: the last phase validates what workers reported, and only then recommends, in one question."""
    import re

    raw = (ROOT / "skills/wrap-up/SKILL.md").read_text()
    body = raw.split("# Wrap-up", 1)[1]
    flat = lambda s: " ".join(s.split())  # prose wraps: compare without line breaks
    parts = re.split(r"(?m)^(\d)\. \*\*", body)
    steps = {int(parts[i]): flat(parts[i + 1]) for i in range(1, len(parts) - 1, 2)}
    assert list(steps) == [1, 2, 3, 4, 5], "wrap-up steps: collect, validate, decide, recap, record, in that order"
    assert steps[1].startswith("Collect") and steps[2].startswith("Validate") and steps[3].startswith("Decide")
    assert steps[4].startswith("Recap, then recommend") and steps[5].startswith("Act on the answer, then record")
    assert "Run by the parent session, never by a worker" in flat(body)
    # each rule sits in its own step, pinned as a whole sentence: "and" turned into "or", a "never" added or an
    # "unless" appended changes the sentence and fails here
    pins = {
        1: ("A `READY_FOR_INTEGRATOR` row whose PR is already merged or closed is old: ignore it.",
            "A report is not evidence: read the real artifact (the PR or branch, the head SHA, the checks).",
            "When the description, the bot summary and the code disagree, the code at the head and the checks win.",
            "confirm the merge commit is on the integration branch (`git merge-base --is-ancestor`) and nothing more."),
        2: ("`git rev-parse HEAD` must equal the PR head and the tree must be clean.",
            "Run one gate at a time with a time limit.",
            "anything that needs live services or secrets is not run, and you say so.",
            "stays inside the ticket's `Touches:`.",
            "`evidence/scripts/proof-valid --base origin/<integration branch>`",
            "A checklist with an empty `Patch-id:`, or none, is \"proof without anchor\": rely on your own rerun.",
            "Rerun the gate the ticket's `Done when:` names, focused.",
            "A criterion the worker rewrote is a decision for the operator, never met.",
            "a job that never ran is neither a pass nor a failure",
            "A failure at the head is a failure.",
            "and no verdict in the PR description covers this patch, run `cross-review` yourself in the mode it names.",
            "A verify-mode verdict covers it while `proof-valid --patch-id` accepts its patch id; a break-mode verdict covers the head it names.",
            "Write down what the worker said it did not verify and what you did not check."),
        3: ("Decide each one**, before anything is merged.",
            "a ticket whose comments show two send-backs goes into the question instead.",
            "Offer to merge only when every criterion is met and the Merge gate of `full-send` is green on the head.",
            "Merging is the operator's call: it goes in the question as an option that names the PR and its head,",
            "Never merge what you could not validate."),
        4: ("ONE recommendation and up to two alternatives",
            "Put every decision the operator owes in ONE question, the recommended option first, asked with the \"Ask the user\" action in `jstack`",
            "Never \"nothing to do, what do you want?\".",
            "No hashes or thread ids."),
        5: ("Merge only the PRs the yes names, and only while the head is still the one it named:",
            "which only adds and never cancels, folds or parks:",
            "Nothing moves to done but the operator's acceptance: integrated work goes to review.",
            "The decisions the operator gave go to the product doc.",
            "Remove the worktrees and branches this session created or merged once the comment holds the proof summary;"),
    }
    for step, phrases in pins.items():
        for phrase in phrases:
            assert phrase in steps[step], f"wrap-up step {step} lost: {phrase}"
    # it points at the skills that own a rule instead of restating them
    for step, skills in {2: ("evidence", "babysit-pr", "cross-review"), 3: ("full-send", "fanout"),
                         4: ("groom", "jstack"), 5: ("babysit-pr", "full-send", "fanout", "ticket-start")}.items():
        for skill in skills:
            assert f"`{skill}" in steps[step], f"wrap-up step {step} no longer points at {skill}"
    # there is no merge before the question: the merge is in step 5, after the recap and the one question
    assert not re.search(r"(?i)\bmerge (it|them|the PR)s? (now|first)", flat(body))
    # it does not claim what the other skills deny: workers may start cross-review for high-risk work
    assert "Workers do not start reviewers" not in flat(body)
    fan = (ROOT / "skills/fanout/SKILL.md").read_text().split("## Final report")[1]
    assert "When the wave drains, run `wrap-up` after this table: it validates what the workers reported and recommends the next step." in flat(fan)
    template = [l for l in (ROOT / "templates/AGENTS.md").read_text().splitlines() if l.startswith("- When a wave drains")]
    assert template == ["- When a wave drains, or the operator asks what is next, run `wrap-up`."]


def test_a_reviewer_is_probed_before_it_is_started_and_the_ledger_shows_it():
    """2026-11-08: 8 of 8 reviewers started on a provider with no quota since 11-06 had no probe call before them, 4 of the
    parents had loaded cross-review. Step 2 said "ask quota-gate" with no command, so the model guessed "quota looks unknown"
    from the model list, started it, ended its turn, and the silent review sat for 34 minutes."""
    flat = lambda s: " ".join(s.split())
    review = flat((ROOT / "skills/cross-review/SKILL.md").read_text())
    step2 = review.split("2. **Skip what is known to be out.**")[1].split("3. **Try it.**")[0]
    for phrase in ("Before you start any candidate, run `<quota_probe> --provider <provider>` for each candidate's provider",
                   "Exit 1 (at 0% or marked exhausted): skip it.",
                   "never judge a provider from it and never start a candidate you did not probe."):
        assert phrase in step2, f"cross-review step 2 lost: {phrase}"
    step3 = review.split("3. **Try it.**")[1].split("4. **Independence ladder.**")[0]
    assert "do not end your turn" in step3 and '"Check that a started agent answered" action in `jstack`' in step3
    assert "Probed: <provider=exit code, for every candidate considered>" in review
    actions = flat((ROOT / "skills/jstack/SKILL.md").read_text())
    assert "| Check that a started agent answered |" in actions and "2-minute timeout" in actions.split("| Check that a started agent answered |")[1].split("\n")[0]


# The rules in templates/AGENTS.md are the ones every repo's agents read, and each repo holds a copy. `template-drift` and
# `doctor` tell a repo its copy is old by comparing the marker on the template's first line, so the marker must move when
# the template does. When this fails: bump the marker to the release that changes the template, say so under that release in
# CHANGELOG.md (mention `templates/AGENTS.md`), and pin the new hash here.
TEMPLATE_BODY_SHA256 = "301bb388d18157577f62ab92d30607fe32a9eff5a908fc820006f05a1464651b"


def test_the_template_marker_moves_when_the_template_does():
    import hashlib
    text = (ROOT / "templates/AGENTS.md").read_text()
    first, body = text.split("\n", 1)
    found = re.fullmatch(r"<!-- jstack-template: (\d+\.\d+\.\d+) -->", first)
    assert found, "templates/AGENTS.md must start with `<!-- jstack-template: X.Y.Z -->`"
    assert hashlib.sha256(body.encode()).hexdigest() == TEMPLATE_BODY_SHA256, (
        "templates/AGENTS.md changed: bump its marker, mention `templates/AGENTS.md` under that release in CHANGELOG.md, and pin the new hash")
    version = found.group(1)
    section = (ROOT / "CHANGELOG.md").read_text().split(f"## {version}\n", 1)
    assert len(section) == 2, f"CHANGELOG.md has no section for the template marker {version}"
    assert "templates/AGENTS.md" in section[1].split("\n## ", 1)[0], f"the {version} section does not mention templates/AGENTS.md"
    assert tuple(map(int, version.split("."))) <= tuple(map(int, (ROOT / "VERSION").read_text().split("."))), "the marker is ahead of VERSION"


def test_a_ticket_is_proven_where_it_has_to_work():
    """0.10.3: what a run can settle is not handed to the operator; a proof on another surface is a stand-in."""
    read = lambda rel: " ".join((ROOT / rel).read_text().split())
    evidence = read("skills/evidence/SKILL.md")
    for needle in ("**Prove it where it has to work.**", "`scripts/checklist-init <ticket> --surface <name>`", "give it a row at level 5",
                   "Proof elsewhere is a stand-in: it does not pass", "`BLOCKED(env)` with what you tried, never a quiet switch to another surface",
                   "never a note that leaves the check to the operator"):
        assert needle in evidence, needle
    assert "on this surface: <the one the ticket names, or the repo's main one>" in read("skills/cross-review/SKILL.md")
    assert "start with `checklist-init <ticket> --surface <name>` and prove it there" in read("skills/fanout/SKILL.md")
    assert "`--checklist <file> --surface <name>`" in read("skills/wrap-up/SKILL.md") and "It is not passed on to the operator to try." in read("skills/wrap-up/SKILL.md")
    assert "the checklist has a level 5 row on that surface" in read("skills/full-send/SKILL.md")

