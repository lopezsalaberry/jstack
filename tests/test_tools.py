"""Behavior of the tools the skills ship. Each test runs the real script."""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "skills/jstack/scripts/jstack-settings"
DOCTOR = ROOT / "skills/jstack/scripts/doctor"
PROBE = ROOT / "skills/quota-gate/scripts/quota-probe"
WAVE = ROOT / "skills/fanout/scripts/wave-status"
PRWAIT = ROOT / "skills/babysit-pr/scripts/pr-wait"
PROOFVALID = ROOT / "skills/evidence/scripts/proof-valid"
TRAIL = ROOT / "skills/jstack/scripts/trail"
CHECKLIST = ROOT / "skills/evidence/scripts/checklist-init"
TOKENLINT = ROOT / "skills/full-send/scripts/token-lint"
TEMPLATE_DRIFT = ROOT / "skills/jstack/scripts/template-drift"
TEMPLATE = ROOT / "templates/AGENTS.md"


def run(cmd, cwd=None, env=None, timeout=60):
    base = {"PATH": os.environ["PATH"], "HOME": str(cwd or ROOT)}
    base.update(env or {})
    return subprocess.run([sys.executable, *map(str, cmd)], cwd=cwd, env=base, capture_output=True, text=True, timeout=timeout)


def git(path, *args):
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def repo(tmp_path, agents=""):
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "user.email", "t@example.com")
    git(r, "config", "user.name", "T")
    (r / "AGENTS.md").write_text(agents or "# Project\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "init")
    return r


# --- settings ---------------------------------------------------------------

def test_settings_precedence_is_env_then_agents_md_then_default(tmp_path):
    r = repo(tmp_path, "# P\n\n## jstack settings\nintegration_branch: develop\nmodels: a:m1, b:m2  # order matters\n"
                       "iteration_minutes: 45\n\n## Other\niteration_minutes: 999\n")
    out = json.loads(run([SETTINGS, "--repo", r, "--json"], cwd=tmp_path).stdout)
    assert out["integration_branch"] == "develop"
    assert out["models"] == "a:m1, b:m2"          # inline comment stripped
    assert out["iteration_minutes"] == "45"       # a later heading does not leak in
    assert out["paid_fallback"] == "off" and out["review_bots"] == ""
    env = run([SETTINGS, "--repo", r, "iteration_minutes"], cwd=tmp_path, env={"JSTACK_ITERATION_MINUTES": "5"})
    assert env.stdout.strip() == "5"


def test_settings_without_a_block_use_defaults_and_unknown_keys_fail(tmp_path):
    r = repo(tmp_path)
    assert run([SETTINGS, "--repo", r, "integration_branch"], cwd=tmp_path).stdout.strip() == "main"
    assert run([SETTINGS, "--repo", r, "quota_probe"], cwd=tmp_path).stdout.strip().endswith("quota-gate/scripts/quota-probe")
    bad = run([SETTINGS, "--repo", r, "nope"], cwd=tmp_path)
    assert bad.returncode == 2 and "unknown key" in bad.stderr


# --- quota probe ------------------------------------------------------------

def test_quota_probe_exit_codes_and_unknown_is_not_exhausted(tmp_path):
    src = tmp_path / "q.txt"
    src.write_text("# comment\nalpha acct1 0\nalpha acct2 0%\nbeta acct1 40\n\n")
    ok = lambda p: run([PROBE, "--source", src, "--provider", p], cwd=tmp_path).returncode
    assert ok("beta") == 0
    assert ok("alpha") == 1          # every account at 0
    assert ok("gamma") == 2          # not listed: unknown, not exhausted
    assert run([PROBE, "--source", src], cwd=tmp_path).stdout.splitlines()[0] == "alpha acct1 0"
    old = time.time() - 3 * 3600
    os.utime(src, (old, old))
    assert ok("beta") == 2           # stale data is unknown, never "available" or "exhausted"
    assert run([PROBE, "--provider", "beta"], cwd=tmp_path).returncode == 2   # no source at all


def test_the_shipped_probe_hands_the_call_to_the_configured_one(tmp_path):
    """2026-11-08: a session ran the shipped probe directly, read "unknown (no quota source configured)" and carried it for
    two days while the configured probe said the provider was at 0%. Whichever probe a caller reaches must answer alike."""
    fake = tmp_path / "fake-probe"
    fake.write_text("#!/usr/bin/env python3\nimport sys\nprint('configured', *sys.argv[1:])\nsys.exit(1)\n")
    fake.chmod(0o755)
    direct = run([PROBE, "--provider", "codex"], cwd=tmp_path, env={"JSTACK_QUOTA_PROBE": str(fake)})
    assert direct.returncode == 1 and direct.stdout.strip() == "configured --provider codex", (direct.stdout, direct.stderr)
    marked = run([PROBE, "--mark-exhausted", "codex", "--minutes", "5"], cwd=tmp_path, env={"JSTACK_QUOTA_PROBE": str(fake)})
    assert marked.stdout.strip() == "configured --mark-exhausted codex --minutes 5"
    listing = run([PROBE], cwd=tmp_path, env={"JSTACK_QUOTA_PROBE": str(fake)})
    assert listing.returncode == 1 and listing.stdout.strip() == "configured", "a call with no arguments reaches it too"
    r = repo(tmp_path, f"# P\n\n## jstack settings\nquota_probe: {fake}\n")
    assert run([PROBE, "--provider", "codex"], cwd=r).returncode == 1, "the AGENTS.md setting is reached too"
    src = tmp_path / "q.txt"
    src.write_text("codex acct 50\n")
    explicit = run([PROBE, "--source", src, "--provider", "codex"], cwd=tmp_path, env={"JSTACK_QUOTA_PROBE": str(fake)})
    assert explicit.returncode == 0, "an explicit --source is a request for this file, not for the configured probe"
    itself = run([PROBE, "--provider", "codex"], cwd=tmp_path, env={"JSTACK_QUOTA_PROBE": str(PROBE)})
    assert itself.returncode == 2, "a setting that names this script must not loop"
    wrapper = tmp_path / "wrapper-probe"                     # a configured probe that calls the shipped one again
    wrapper.write_text(f"#!/usr/bin/env python3\nimport os, sys\nos.execv(sys.executable, [sys.executable, {str(PROBE)!r}, *sys.argv[1:]])\n")
    wrapper.chmod(0o755)
    chained = run([PROBE, "--provider", "codex"], cwd=tmp_path, env={"JSTACK_QUOTA_PROBE": str(wrapper)}, timeout=10)
    assert chained.returncode == 2, "a hand-off must not hand off again"
    missing = run([PROBE, "--provider", "codex"], cwd=tmp_path, env={"JSTACK_QUOTA_PROBE": str(tmp_path / "gone")})
    assert missing.returncode == 2, "a configured probe that does not exist falls back to this script (doctor reports it)"


def test_quota_probe_rejects_a_malformed_line(tmp_path):
    src = tmp_path / "q.txt"
    src.write_text("alpha only-two-fields\n")
    bad = run([PROBE, "--source", src, "--provider", "alpha"], cwd=tmp_path)
    assert bad.returncode == 2 and "expected" in bad.stderr


def test_a_refusal_marks_the_provider_and_every_later_worker_skips_it(tmp_path):
    marks = {"JSTACK_QUOTA_MARKS": str(tmp_path / "marks.txt")}
    src = tmp_path / "q.txt"
    src.write_text("alpha acct1 80\nbeta acct1 50\n")
    probe = lambda p: run([PROBE, "--source", src, "--provider", p], cwd=tmp_path, env=marks).returncode
    assert probe("alpha") == 0
    run([PROBE, "--mark-exhausted", "alpha", "--reason", "quota exceeded"], cwd=tmp_path, env=marks)
    assert probe("alpha") == 1                      # the source says 80%, the refusal wins
    assert probe("beta") == 0                       # other providers are untouched
    other_repo = tmp_path / "elsewhere"
    other_repo.mkdir()
    assert run([PROBE, "--source", src, "--provider", "alpha"], cwd=other_repo, env=marks).returncode == 1  # per machine
    assert "quota exceeded" in run([PROBE, "--source", src, "--provider", "alpha"], cwd=tmp_path, env=marks).stderr
    run([PROBE, "--clear", "alpha"], cwd=tmp_path, env=marks)
    assert probe("alpha") == 0


def test_a_mark_works_without_any_quota_source_and_expires(tmp_path):
    marks = {"JSTACK_QUOTA_MARKS": str(tmp_path / "marks.txt")}
    run([PROBE, "--mark-exhausted", "gamma", "--minutes", "60"], cwd=tmp_path, env=marks)
    assert run([PROBE, "--provider", "gamma"], cwd=tmp_path, env=marks).returncode == 1   # no source at all
    (tmp_path / "marks.txt").write_text(f"gamma {int(time.time()) - 5} expired\n")
    assert run([PROBE, "--provider", "gamma"], cwd=tmp_path, env=marks).returncode == 2   # back to unknown


def test_until_marks_a_provider_for_as_long_as_its_refusal_lasts(tmp_path):
    """2026-11-12: a monthly cap (back on the 1st) was marked for the default hour, so the next worker tried it again."""
    marks = {"JSTACK_QUOTA_MARKS": str(tmp_path / "marks.txt")}
    later = time.strftime("%Y-%m-%dT%H:%M", time.localtime(time.time() + 20 * 86400))
    done = run([PROBE, "--mark-exhausted", "cursor", "--until", later, "--reason", "monthly cap"], cwd=tmp_path, env=marks)
    assert done.returncode == 0 and "marked exhausted until" in done.stdout, (done.stdout, done.stderr)
    expires = float((tmp_path / "marks.txt").read_text().split()[1])
    assert 19 * 86400 < expires - time.time() < 21 * 86400, "about 20 days, not the hour --minutes would give"
    assert run([PROBE, "--provider", "cursor"], cwd=tmp_path, env=marks).returncode == 1
    far = time.strftime("%Y-%m-%d", time.localtime(time.time() + 90 * 86400))
    for text, why in (("2020-01-01", "already past"), (far, "days away"), ("tomorrow-ish", "not an ISO")):
        bad = run([PROBE, "--mark-exhausted", "x", "--until", text], cwd=tmp_path, env=marks)
        assert bad.returncode == 64 and why in bad.stderr, (text, bad.stderr)   # 64, never the 2 that means "unknown"
    both = run([PROBE, "--mark-exhausted", "x", "--minutes", "5", "--until", later], cwd=tmp_path, env=marks)
    assert both.returncode == 64 and "exclusive" in both.stderr
    epoch = run([PROBE, "--mark-exhausted", "y", "--until", str(int(time.time()) + 7200)], cwd=tmp_path, env=marks)
    assert epoch.returncode == 0, "epoch seconds are accepted too"
    assert run([PROBE, "--mark-exhausted", "z"], cwd=tmp_path, env=marks).stdout.strip().endswith("for 60 min")


def test_reviewer_models_defaults_to_auto_and_the_preference_syntax_parses(tmp_path):
    r = repo(tmp_path, "# P\n\n## jstack settings\nreviewer_models: provider-a:model-x, auto\n")
    assert run([SETTINGS, "--repo", r, "reviewer_models"], cwd=tmp_path).stdout.strip() == "provider-a:model-x, auto"
    other = tmp_path / "second"
    other.mkdir()
    plain = repo(other)
    assert run([SETTINGS, "--repo", plain, "reviewer_models"], cwd=tmp_path).stdout.strip() == "auto"


def test_the_operators_own_settings_sit_between_the_repo_and_the_default(tmp_path):
    """2026-11-14: the reviewer order lived in a note and in one repo, so a refusal turned into a question. The operator's
    preference must reach every repo without editing each AGENTS.md, and a repo may still replace it."""
    user = tmp_path / "mine.txt"
    user.write_text("# my defaults\nreviewer_models: codex, cursor, auto  # my order\nrouting: UI and UX work: the strongest model\n"
                    "models: pinned:one\n")
    r = repo(tmp_path, "# P\n\n## jstack settings\nmodels: repo:two\n")
    env = {"JSTACK_USER_SETTINGS": str(user)}
    out = json.loads(run([SETTINGS, "--repo", r, "--json"], cwd=tmp_path, env=env).stdout)
    assert out["reviewer_models"] == "codex, cursor, auto"        # from the operator's file, inline comment stripped
    assert out["routing"] == "UI and UX work: the strongest model"
    assert out["models"] == "repo:two"                            # the repo's value replaces the operator's
    over = run([SETTINGS, "--repo", r, "reviewer_models"], cwd=tmp_path, env={**env, "JSTACK_REVIEWER_MODELS": "x"})
    assert over.stdout.strip() == "x"                             # the environment still wins
    assert run([SETTINGS, "--repo", r, "routing"], cwd=tmp_path).stdout.strip() == ""    # no file: the default
    home_file = tmp_path / ".config" / "jstack" / "settings"      # HOME is the working directory in these tests
    home_file.parent.mkdir(parents=True)
    home_file.write_text("routing: from the home file\n")
    assert run([SETTINGS, "--repo", r, "routing"], cwd=tmp_path).stdout.strip() == "from the home file"


# --- doctor -----------------------------------------------------------------

def tools_dir(tmp_path, with_gh):
    b = tmp_path / "bin"
    b.mkdir()
    for name, target in (("git", subprocess.run(["which", "git"], capture_output=True, text=True).stdout.strip()),
                         ("python3", sys.executable)):
        (b / name).symlink_to(target)
    if with_gh:
        gh = b / "gh"
        gh.write_text("#!/bin/sh\nexit 0\n")
        gh.chmod(0o755)
    return b


def test_doctor_names_what_is_missing(tmp_path):
    r = repo(tmp_path)
    missing = run([DOCTOR, "--repo", r], cwd=tmp_path, env={"PATH": str(tools_dir(tmp_path, False))})
    assert missing.returncode == 1 and "FAIL gh" in missing.stdout
    fine = tmp_path / "fine"
    fine.mkdir()
    present = run([DOCTOR, "--repo", r], cwd=tmp_path, env={"PATH": str(tools_dir(fine, True))})
    assert present.returncode == 0, present.stdout
    assert "warn jstack settings in AGENTS.md" in present.stdout   # warns, does not block
    assert "ok   quota_probe runs" in present.stdout


# --- wave status ------------------------------------------------------------

def test_wave_status_reads_runstate_of_every_worktree(tmp_path):
    r = repo(tmp_path)
    wt = tmp_path / "wt-a"
    git(r, "worktree", "add", "-q", str(wt), "-b", "feat/a")
    (wt / "RUNSTATE.md").write_text("Status: WAITING quota probe passes\nMetric: failing tests\nBaseline: 12\nNow: 4\n"
                                    "Next step: rerun the suite\n\nNotes follow.\n")
    rows = json.loads(run([WAVE, "--repo", r, "--json"], cwd=tmp_path).stdout)
    by_branch = {x["branch"]: x for x in rows}
    assert by_branch["feat/a"]["status"] == "WAITING quota probe passes"
    assert by_branch["feat/a"]["metric"] == "failing tests: 12 -> 4"
    assert by_branch["main"]["status"] == "no RUNSTATE.md"
    table = run([WAVE, "--repo", r], cwd=tmp_path).stdout
    assert "| feat/a | WAITING quota probe passes | failing tests: 12 -> 4 | rerun the suite |" in table
    assert run([WAVE, "--repo", tmp_path / "nope"], cwd=tmp_path).returncode == 2


# --- pr-wait with a fake gh ---------------------------------------------------

FAKE_GH = '''#!/usr/bin/env python3
import json, os, sys
fx = json.load(open(os.environ["FAKE_GH"]))
a = sys.argv[1:]
def out(x):
    print(x if isinstance(x, str) else json.dumps(x)); sys.exit(0)
if a[:2] == ["pr", "view"]: out({"number": 7})
if a[:2] == ["api", "graphql"]: out({"data": {"viewer": {"login": "me"}, "repository": {"pullRequest": fx["pr"]}}})
if a[:2] == ["pr", "checks"]: out(fx["checks"])
if a[0] == "api" and ("rules/branches" in a[1] or "required_status_checks" in a[1]):
    sys.stderr.write("gh: Not Found (HTTP 404)\\n"); sys.exit(1)
if a[0] == "api" and "/compare/" in a[1]: out("0")
sys.stderr.write("fake gh: unhandled " + " ".join(a) + "\\n"); sys.exit(1)
'''


def fake_gh(tmp_path, checks):
    b = tmp_path / "ghbin"
    b.mkdir()
    gh = b / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)
    fx = tmp_path / "fx.json"
    fx.write_text(json.dumps({
        "checks": checks,
        "pr": {"url": "https://github.com/o/r/pull/7", "state": "OPEN", "headRefOid": "abc1234def", "baseRefName": "main",
               "mergeStateStatus": "CLEAN", "author": {"login": "author"}, "baseRef": {"target": {"oid": "base111"}},
               "comments": {"nodes": []}, "reviews": {"nodes": []}, "reviewThreads": {"nodes": []}}}))
    return {"PATH": f"{b}:{os.environ['PATH']}", "FAKE_GH": str(fx), "HOME": str(tmp_path)}


def test_pr_wait_ready_does_not_wait_for_bots_that_are_not_configured(tmp_path):
    env = fake_gh(tmp_path, [{"name": "ci", "bucket": "pass", "link": "u", "description": ""}])
    done = run([PRWAIT, "7", "--repo", "o/r", "--interval", "5"], cwd=tmp_path, env=env, timeout=40)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "ready on abc1234" in done.stdout and "no review bots configured" in done.stdout


def test_pr_wait_with_a_configured_bot_waits_until_it_has_reviewed(tmp_path):
    env = fake_gh(tmp_path, [{"name": "ci", "bucket": "pass", "link": "u", "description": ""}])
    try:
        run([PRWAIT, "7", "--repo", "o/r", "--interval", "5", "--bots", "reviewbot"], cwd=tmp_path, env=env, timeout=8)
    except subprocess.TimeoutExpired:
        return
    raise AssertionError("pr-wait finished although the configured bot never reviewed")


def test_pr_wait_reports_a_failed_check_and_exits_1(tmp_path):
    env = fake_gh(tmp_path, [{"name": "ci", "bucket": "fail", "link": "http://x/run/1", "description": ""}])
    done = run([PRWAIT, "7", "--repo", "o/r", "--interval", "5"], cwd=tmp_path, env=env, timeout=20)
    assert done.returncode == 1 and "check failed: ci http://x/run/1" in done.stdout


# --- proof follows the patch, not the commit -----------------------------------

def commit_all(path, message="x"):
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", message)


def test_proof_follows_the_patch_not_the_commit(tmp_path):
    r = repo(tmp_path)
    git(r, "checkout", "-q", "-b", "feat")
    (r / "a.txt").write_text("1\n")
    commit_all(r)
    checklist = tmp_path / "checklist.md"
    checklist.write_text("Revision: whatever\n" + run([PROOFVALID, "--print", "--base", "main"], cwd=r).stdout)
    check = lambda: run([PROOFVALID, "--checklist", checklist, "--base", "main"], cwd=r)
    assert check().returncode == 0
    # main moves on with unrelated work and the branch is rebased: new SHA, same change
    git(r, "checkout", "-q", "main")
    (r / "other.txt").write_text("o\n")
    commit_all(r)
    git(r, "checkout", "-q", "feat")
    assert check().returncode == 0, "main moving on must not invalidate a proof before any rebase"
    git(r, "rebase", "-q", "main")
    assert check().returncode == 0, "a rebase alone must not invalidate a proof"
    (r / "a.txt").write_text("2\n")
    commit_all(r)
    stale = check()
    assert stale.returncode == 1 and "prove again" in stale.stdout, "a real edit must invalidate it"


def test_proof_valid_refuses_a_checklist_that_names_no_patch(tmp_path):
    r = repo(tmp_path)
    checklist = tmp_path / "c.md"
    checklist.write_text("Revision: abc\nPASS something\n")
    bad = run([PROOFVALID, "--checklist", checklist, "--base", "main"], cwd=r)
    assert bad.returncode == 2 and "Patch-id" in bad.stderr


# --- decision trail --------------------------------------------------------------

def test_trail_only_appends_and_neutralizes_formulas(tmp_path):
    log = tmp_path / "TRAIL.tsv"
    run([TRAIL, log, "frame", "counted the work", "to size it", "commit 3a9f1c2", "found 5 things"], cwd=tmp_path)
    first = log.read_text()
    run([TRAIL, log, "build", "=HYPERLINK(\"x\")", "multi\nline\twhy", "pr 12", "green"], cwd=tmp_path)
    after = log.read_text()
    assert after.startswith(first), "earlier rows must never change"
    rows = [r.split("\t") for r in after.splitlines()]
    assert rows[0][:3] == ["ts", "phase", "decision"] and len(rows) == 3
    assert rows[2][2] == "'=HYPERLINK(\"x\")" and rows[2][3] == "multi line why"
    assert all(len(r) == 6 for r in rows)
    assert run([TRAIL, "--check", log], cwd=tmp_path).returncode == 0
    log.write_text(after + "not\ta\trow\n")
    assert run([TRAIL, "--check", log], cwd=tmp_path).returncode == 1


# --- token lint: the mechanical half of the UI gate ---------------------------------

TOKENS = ('{"color": {"primary": {"$value": "#3366ff"}, "text": {"value": "#111111"}},'
          ' "space": {"md": "16px", "lg": {"$value": "24px"}}, "font": {"body": "Inter, sans-serif"}}')


def ui_repo(tmp_path):
    r = repo(tmp_path)
    (r / "design").mkdir()
    (r / "design/tokens.json").write_text(TOKENS)
    (r / "old.css").write_text("a { color: #abcdef; }\n")        # an existing violation: never blocks
    commit_all(r, "base")
    git(r, "checkout", "-q", "-b", "feat")
    return r


def lint(r, *extra):
    return run([TOKENLINT, "--base", "main", *extra], cwd=r)


def test_token_lint_passes_tokens_and_ignores_old_and_non_ui_lines(tmp_path):
    r = ui_repo(tmp_path)
    (r / "ok.css").write_text(".btn { color: #3366FF; padding: 16px; margin: 0; font-family: Inter, sans-serif; }\n"
                              ".t { color: var(--text); gap: 24px; }\n")
    (r / "notes.md").write_text("see #ff0000 and 13px\n")      # not a UI file
    commit_all(r)
    done = lint(r)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "no new off-token literals" in done.stdout


def test_token_lint_blocks_off_token_literals_and_suggests_the_nearest_color(tmp_path):
    r = ui_repo(tmp_path)
    (r / "bad.css").write_text(".x { color: #3367ff; padding: 13px; font-family: 'Comic Sans'; background: rgb(1, 2, 3); }\n")
    commit_all(r)
    out = lint(r)
    assert out.returncode == 1
    assert "#3367ff" in out.stdout and "nearest: color.primary" in out.stdout
    assert "13px" in out.stdout and "comic sans" in out.stdout and "rgb(1, 2, 3)" in out.stdout
    assert "#abcdef" not in out.stdout                          # the old line is not this change's fault
    assert "bad.css:1" in out.stdout


def test_token_lint_sees_untracked_and_uncommitted_files(tmp_path):
    r = ui_repo(tmp_path)
    (r / "new.css").write_text(".x { color: #010203; }\n")      # never added to git
    assert lint(r).returncode == 1


def test_token_lint_exceptions_need_a_reason(tmp_path):
    r = ui_repo(tmp_path)
    (r / "bad.css").write_text(".x { padding: 13px; }\n")
    commit_all(r)
    (r / "design/token-allow.txt").write_text("bad.css 13px  # legacy widget, ticket 42\n")
    assert lint(r).returncode == 0
    (r / "design/token-allow.txt").write_text("bad.css 13px\n")
    no_reason = lint(r)
    assert no_reason.returncode == 2 and "reason" in no_reason.stderr


def test_token_lint_without_tokens_is_a_usage_error_not_a_pass(tmp_path):
    r = repo(tmp_path)
    missing = lint(r)
    assert missing.returncode == 2 and "design tokens first" in missing.stderr


def test_token_lint_reads_the_token_files_real_projects_use(tmp_path):
    """Lists of font families, numeric weights, and a system that defines no size tokens at all."""
    r = repo(tmp_path)
    (r / "design").mkdir()
    (r / "design/tokens.json").write_text(
        '{"color": {"bg": {"$value": "#ffffff"}}, "font": {"sans": ["Geist Variable", "ui-sans-serif"],'
        ' "weight": {"regular": 400}}, "space": {"1": "4px"}, "radius": {"md": 8}}')
    commit_all(r, "base")
    git(r, "checkout", "-q", "-b", "feat")
    (r / "a.css").write_text(".a { font-family: 'Geist Variable', sans-serif; padding: 4px; border-radius: 8px; }\n")
    commit_all(r)
    assert lint(r).returncode == 0, lint(r).stdout
    (r / "b.css").write_text(".b { padding: 400px; }\n")            # a weight is not a length token
    commit_all(r)
    assert lint(r).returncode == 1
    colors_only = tmp_path / "second"
    colors_only.mkdir()
    r2 = repo(colors_only)
    (r2 / "design").mkdir()
    (r2 / "design/tokens.json").write_text('{"color": {"bg": "#ffffff"}}')
    commit_all(r2, "base")
    git(r2, "checkout", "-q", "-b", "feat")
    (r2 / "c.css").write_text(".c { padding: 13px; font-family: Comic; color: #ffffff; }\n")
    commit_all(r2)
    assert lint(r2).returncode == 0, "no size or font tokens defined, so none are enforced"


def test_token_lint_skips_token_definition_files_and_hairlines(tmp_path):
    r = ui_repo(tmp_path)
    (r / "tokens.css").write_text(":root { --brand: #123456; --pad: 13px; }\n")        # defines tokens on purpose
    (r / "line.css").write_text(".l { border-width: 1px; top: 1px; }\n")               # a hairline is not a design choice
    commit_all(r)
    assert lint(r).returncode == 0, lint(r).stdout
    (r / "wide.css").write_text(".w { width: 13px; }\n")
    commit_all(r)
    assert lint(r).returncode == 1


def test_token_lint_does_not_treat_test_files_as_ui(tmp_path):
    """2026-11-10, run over the last 40 commits of two real repos: 10 violations, every one inside a test file (a color
    a test asserts on, `rgb(colors.x)` in a helper). A test is not a UI change and must not block a merge."""
    r = ui_repo(tmp_path)
    (r / "__tests__").mkdir()
    (r / "__tests__/panel.css").write_text(".t { color: #123456; }\n")
    (r / "panel.test.tsx").write_text("expect(style.color).toBe('#123456'); // padding: 13px;\n")
    (r / "panel.spec.css").write_text(".t { width: 13px; }\n")
    commit_all(r)
    assert lint(r).returncode == 0, lint(r).stdout
    (r / "panel.css").write_text(".t { color: #123456; }\n")
    assert lint(r).returncode == 1


def test_checklist_init_starts_a_proof_that_proof_valid_accepts(tmp_path):
    r = repo(tmp_path)
    git(r, "checkout", "-q", "-b", "feat")
    (r / "a.txt").write_text("1\n")
    commit_all(r)
    made = run([CHECKLIST, "T-9", "--base", "main"], cwd=r)
    assert made.returncode == 0, made.stderr
    text = (r / ".artifacts/T-9/checklist.md").read_text()
    assert "Patch-id: " in text and "Revision: " in text and "A target is PASS only at level 4 or 5" in text
    assert run([PROOFVALID, "--checklist", r / ".artifacts/T-9/checklist.md", "--base", "main"], cwd=r).returncode == 0
    assert ".artifacts/" in (r / ".git/info/exclude").read_text()          # never committed
    assert subprocess.run(["git", "-C", str(r), "status", "--porcelain"], capture_output=True, text=True).stdout.strip() == ""
    again = run([CHECKLIST, "T-9", "--base", "main"], cwd=r)
    assert again.returncode == 1 and "already exists" in again.stderr
    (r / "a.txt").write_text("2\n")
    commit_all(r)
    assert run([PROOFVALID, "--checklist", r / ".artifacts/T-9/checklist.md", "--base", "main"], cwd=r).returncode == 1


def test_a_checklist_started_before_the_change_is_never_called_valid(tmp_path):
    """0.9.1: checklist-init runs first, when the patch is still empty and the revision is the base's tip. The first
    proof-valid after the change then answered "landed" (that revision is in the base) and exited 0, for any patch."""
    r = repo(tmp_path)
    git(r, "checkout", "-q", "-b", "feat")
    started = run([CHECKLIST, "T-1", "--base", "main"], cwd=r)
    assert started.returncode == 0 and "proof-valid --stamp" in started.stderr, started.stderr
    checklist = r / ".artifacts/T-1/checklist.md"
    assert "Patch-id: empty" in checklist.read_text()
    (r / "a.txt").write_text("1\n")
    commit_all(r)
    check = lambda: run([PROOFVALID, "--checklist", checklist, "--base", "main"], cwd=r)
    unanchored = check()
    assert unanchored.returncode == 2 and "--stamp" in unanchored.stderr and "landed" not in unanchored.stdout
    stamped = run([PROOFVALID, "--stamp", checklist, "--base", "main"], cwd=r)
    assert stamped.returncode == 0 and "stamped" in stamped.stdout, stamped.stderr
    assert "Patch-id: empty" not in checklist.read_text() and "A target is PASS only at level 4 or 5" in checklist.read_text()
    assert check().returncode == 0
    (r / "a.txt").write_text("2\n")
    commit_all(r)
    assert check().returncode == 1, "an edit after the stamp must invalidate the proof"


def test_stamp_refuses_when_there_is_nothing_to_prove_and_adds_missing_lines(tmp_path):
    r = repo(tmp_path)
    checklist = tmp_path / "c.md"
    checklist.write_text("# Evidence\n")
    nothing = run([PROOFVALID, "--stamp", checklist, "--base", "main"], cwd=r)
    assert nothing.returncode == 2 and "nothing to stamp" in nothing.stderr
    git(r, "checkout", "-q", "-b", "feat")
    (r / "a.txt").write_text("1\n")
    commit_all(r)
    assert run([PROOFVALID, "--stamp", checklist, "--base", "main"], cwd=r).returncode == 0
    text = checklist.read_text()
    assert text.count("Revision: ") == 1 and text.count("Patch-id: ") == 1
    assert run([PROOFVALID, "--checklist", checklist, "--base", "main"], cwd=r).returncode == 0


def test_a_proof_whose_change_already_landed_still_stands(tmp_path):
    r = repo(tmp_path)
    git(r, "checkout", "-q", "-b", "feat")
    (r / "a.txt").write_text("1\n")
    commit_all(r)
    checklist = tmp_path / "c.md"
    checklist.write_text(run([PROOFVALID, "--print", "--base", "main"], cwd=r).stdout)
    git(r, "checkout", "-q", "main")
    git(r, "merge", "-q", "--ff-only", "feat")                       # the ticket was integrated
    done = run([PROOFVALID, "--checklist", checklist, "--base", "main"], cwd=r)
    assert done.returncode == 0 and "landed" in done.stdout, done.stdout
    other = tmp_path / "o.md"                                          # a proof whose revision is not in main is still stale
    other.write_text("Revision: " + "0" * 40 + "\nPatch-id: deadbeef\n")
    assert run([PROOFVALID, "--checklist", other, "--base", "main"], cwd=r).returncode == 1


def test_the_stack_works_from_a_path_with_spaces(tmp_path):
    """Found on a machine whose checkout lives on an external disk named 'Crucial X9'."""
    import shutil as _shutil
    spaced = tmp_path / "Crucial X9" / "base"
    _shutil.copytree(ROOT / "skills", spaced / "skills", ignore=_shutil.ignore_patterns("__pycache__"))
    r = repo(tmp_path)
    probe = run([spaced / "skills/jstack/scripts/jstack-settings", "--repo", r, "quota_probe"], cwd=tmp_path).stdout.strip()
    import shlex as _shlex
    assert _shlex.split(probe)[0].endswith("Crucial X9/base/skills/quota-gate/scripts/quota-probe"), probe
    done = run([spaced / "skills/jstack/scripts/doctor", "--repo", r], cwd=tmp_path, env={"PATH": str(tools_dir(tmp_path, True))})
    assert "Traceback" not in done.stderr, done.stderr
    assert "ok   quota_probe runs" in done.stdout, done.stdout
    assert done.returncode == 0, done.stdout


def test_a_probe_that_cannot_run_is_reported_not_a_crash(tmp_path):
    r = repo(tmp_path)
    (r / "AGENTS.md").write_text("# P\n\n## jstack settings\nquota_probe: /no/such/dir/probe\n")
    done = run([DOCTOR, "--repo", r], cwd=tmp_path, env={"PATH": str(tools_dir(tmp_path, True))})
    assert "Traceback" not in done.stderr and "FAIL quota_probe command" in done.stdout and done.returncode == 1


def test_every_shipped_script_survives_deprecation_warnings_as_errors():
    """A newer Python turns today's deprecation warning into tomorrow's crash (found on a Mac with a newer
    Homebrew Python: the doctor used a function that no longer exists there)."""
    scripts = [p for p in ROOT.glob("skills/*/scripts/*") if p.is_file()]
    assert len(scripts) >= 8
    for script in scripts:
        done = subprocess.run([sys.executable, "-W", "error", str(script), "--help"], capture_output=True, text=True,
                              env={"PATH": os.environ["PATH"], "HOME": str(ROOT)}, timeout=60)
        assert "Traceback" not in done.stderr, f"{script.relative_to(ROOT)} crashes with warnings as errors:\n{done.stderr[-400:]}"


def test_doctor_runs_under_warnings_as_errors(tmp_path):
    r = repo(tmp_path)
    done = subprocess.run([sys.executable, "-W", "error", str(DOCTOR), "--repo", str(r)], capture_output=True, text=True,
                          env={"PATH": str(tools_dir(tmp_path, True)), "HOME": str(tmp_path)}, cwd=tmp_path)
    assert "Traceback" not in done.stderr, done.stderr
    assert "ok   quota_probe runs" in done.stdout


def test_quota_probe_usage_error_exits_64_never_2(tmp_path):
    """Exit 2 means 'unknown' in the contract, and argparse's default usage error is exit 2."""
    done = run([PROBE, "--nope"], cwd=tmp_path)
    assert done.returncode == 64 and "usage:" in done.stderr.lower(), done.stderr


def _fake_probe(tmp_path, body):
    p = tmp_path / "fake-probe"
    p.write_text(f"#!{sys.executable}\n" + body)
    p.chmod(0o755)
    return p


def _doctor_with_probe(tmp_path, fake):
    r = repo(tmp_path, f"# P\n\n## jstack settings\nquota_probe: {fake}\n")
    return run([DOCTOR, "--repo", r], cwd=tmp_path, env={"PATH": str(tools_dir(tmp_path, True))})


def test_doctor_fails_a_probe_that_does_not_speak_the_contract(tmp_path):
    """2026-11-07: a probe that only knew --model answered every --provider call with an argparse usage error, exit 2,
    which the contract reads as 'unknown'. The doctor said ok, every provider looked unknown (one account was in a quota
    cooldown) and no refusal was ever marked, so a review kept going to the exhausted provider."""
    fake = _fake_probe(tmp_path, "import argparse\nap = argparse.ArgumentParser()\nap.add_argument('--model')\nap.parse_args()\n")
    done = _doctor_with_probe(tmp_path, fake)
    assert "FAIL quota_probe runs" in done.stdout and "usage error" in done.stdout and done.returncode == 1, done.stdout


def test_doctor_fails_a_probe_that_answers_provider_but_cannot_mark(tmp_path):
    fake = _fake_probe(tmp_path, "import sys\nif sys.argv[1:2] == ['--provider']:\n    sys.exit(2)\nsys.stderr.write('usage: fake [--provider NAME]\\n')\nsys.exit(2)\n")
    done = _doctor_with_probe(tmp_path, fake)
    assert "FAIL quota_probe runs" in done.stdout and "--mark-exhausted" in done.stdout and done.returncode == 1, done.stdout


def test_doctor_leaves_the_real_marks_file_alone(tmp_path):
    """The contract walk uses a throwaway marks file and a throwaway provider name."""
    marks = tmp_path / "real-marks.txt"
    marks.write_text("claude 4102444800 keep me\n")
    r = repo(tmp_path)
    done = run([DOCTOR, "--repo", r], cwd=tmp_path, env={"JSTACK_QUOTA_MARKS": str(marks)})
    assert "ok   quota_probe runs" in done.stdout, done.stdout
    assert marks.read_text() == "claude 4102444800 keep me\n"


# --- the UI gate, the template copy and the version, as the doctor reports them ----------------------

def test_doctor_says_when_the_ui_gate_is_off(tmp_path):
    """2026-11-10: five repos had a design system, none had `ui_paths`, so the gate never applied and 27 sessions that edited
    UI files ran no design check. The gate being off has to be said out loud."""
    r = repo(tmp_path)
    (r / "design").mkdir()
    (r / "design/tokens.json").write_text("{}")
    path = {"PATH": str(tools_dir(tmp_path, True))}
    assert "warn UI design gate: OFF" in run([DOCTOR, "--repo", r], cwd=tmp_path, env=path).stdout
    (r / "AGENTS.md").write_text("# P\n\n## jstack settings\nui_paths: src/**\n")
    assert "ok   UI design gate: on for src/**" in run([DOCTOR, "--repo", r], cwd=tmp_path, env=path).stdout
    (r / "design/tokens.json").unlink()
    assert "warn UI design gate: `ui_paths` is set but" in run([DOCTOR, "--repo", r], cwd=tmp_path, env=path).stdout
    (r / "AGENTS.md").write_text("# P\n")
    assert "ok   UI design gate: no design tokens" in run([DOCTOR, "--repo", r], cwd=tmp_path, env=path).stdout


def _marker_line():
    return TEMPLATE.read_text().splitlines()[0]


def test_template_drift_names_old_copies(tmp_path):
    """2026-11-10: three of five repos still carried the 0.5.4 flow, which lacks every rule added since."""
    current = TEMPLATE.read_text()
    marker = _marker_line()

    def make(name, text):
        d = tmp_path / name
        d.mkdir()
        (d / "AGENTS.md").write_text(text)
        return d

    fresh = make("fresh", current + "\n# Project rules\n")
    old = make("old", current.replace(marker, "<!-- jstack-template: 0.1.0 -->"))
    unmarked = make("unmarked", current.replace(marker + "\n\n", ""))
    newer = make("newer", current.replace(marker, "<!-- jstack-template: 99.0.0 -->"))
    major, minor, _ = map(int, re.search(r"(\d+)\.(\d+)\.(\d+)", marker).groups())
    # A version whose order as numbers differs from its order as text: 0.9.9 against 0.10.x, 0.10.0 against 0.9.x.
    tricky, tricky_status = ((f"{major}.9.9", "stale") if minor >= 10 else (f"{major}.10.0", "ahead"))
    ten = make("ten", current.replace(marker, f"<!-- jstack-template: {tricky} -->"))
    plain = make("plain", "# Something else\n")
    empty = tmp_path / "empty"
    empty.mkdir()
    done = run([TEMPLATE_DRIFT, fresh, old, unmarked, newer, ten, plain, empty], cwd=tmp_path)
    status = {Path(line.split()[1].rstrip(":")).name: line.split()[0] for line in done.stdout.splitlines()}
    assert status == {"fresh": "ok", "old": "stale", "unmarked": "stale", "newer": "ahead", "ten": tricky_status, "plain": "skip", "empty": "skip"}
    assert done.returncode == 1
    assert run([TEMPLATE_DRIFT, fresh, plain], cwd=tmp_path).returncode == 0
    assert run([TEMPLATE_DRIFT, tmp_path / "missing"], cwd=tmp_path).returncode == 2


def test_doctor_warns_about_an_old_or_missing_copy_of_the_template(tmp_path):
    current = TEMPLATE.read_text()
    r = repo(tmp_path, current)
    path = {"PATH": str(tools_dir(tmp_path, True))}
    assert "ok   AGENTS.md matches the current template" in run([DOCTOR, "--repo", r], cwd=tmp_path, env=path).stdout
    (r / "AGENTS.md").write_text(current.replace(_marker_line(), "<!-- jstack-template: 0.1.0 -->"))
    assert "warn AGENTS.md matches the current template: the copy is from 0.1.0" in run([DOCTOR, "--repo", r], cwd=tmp_path, env=path).stdout
    (r / "AGENTS.md").write_text("# P\n")
    assert "warn AGENTS.md matches the current template: AGENTS.md does not use the jstack flow" in run([DOCTOR, "--repo", r], cwd=tmp_path, env=path).stdout


def _checkout(tmp_path, local_version, remote_tags):
    import shutil
    ck = tmp_path / "ck"
    ignore = shutil.ignore_patterns("__pycache__")
    shutil.copytree(ROOT / "skills", ck / "skills", ignore=ignore)
    shutil.copytree(ROOT / "templates", ck / "templates")
    (ck / "VERSION").write_text(local_version + "\n")
    git(ck, "init", "-q", "-b", "main")
    git(ck, "config", "user.email", "t@example.com")
    git(ck, "config", "user.name", "T")
    git(ck, "add", "-A")
    git(ck, "commit", "-q", "-m", "init")
    if remote_tags is not None:
        bare = tmp_path / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True, capture_output=True)
        git(ck, "remote", "add", "origin", str(bare))
        git(ck, "push", "-q", "origin", "main")
        for tag in remote_tags:
            git(ck, "tag", tag)
            git(ck, "push", "-q", "origin", tag)
    return ck


def test_doctor_compares_the_checkout_with_the_newest_tag_when_asked(tmp_path):
    """A machine that does not run the nightly update can sit on an old jstack with no message at all."""
    r = repo(tmp_path)
    path = {"PATH": str(tools_dir(tmp_path, True))}
    (tmp_path / "a").mkdir()
    behind = _checkout(tmp_path / "a", "0.9.3", ["v0.9.2", "v9.9.9"])
    done = run([behind / "skills/jstack/scripts/doctor", "--repo", r, "--check-updates"], cwd=tmp_path, env=path)
    assert "warn jstack is the newest version: this checkout is 0.9.3 and origin has 9.9.9" in done.stdout, done.stdout
    assert done.returncode == 0, "being behind is a warning, never a failure"
    assert "newest version" not in run([behind / "skills/jstack/scripts/doctor", "--repo", r], cwd=tmp_path, env=path).stdout


def test_doctor_is_quiet_about_the_version_when_the_checkout_is_current_or_cannot_ask(tmp_path):
    r = repo(tmp_path)
    path = {"PATH": str(tools_dir(tmp_path, True))}
    (tmp_path / "a").mkdir()
    current = _checkout(tmp_path / "a", "0.10.0", ["v0.9.3", "v0.10.0"])      # 0.10.0 is newer than 0.9.3
    assert "ok   jstack is the newest version: 0.10.0" in run([current / "skills/jstack/scripts/doctor", "--repo", r, "--check-updates"], cwd=tmp_path, env=path).stdout
    (tmp_path / "b").mkdir()
    offline = _checkout(tmp_path / "b", "0.9.3", None)
    out = run([offline / "skills/jstack/scripts/doctor", "--repo", r, "--check-updates"], cwd=tmp_path, env=path)
    assert "warn jstack is the newest version: could not ask origin" in out.stdout and out.returncode == 0, out.stdout


# --- screenshots in the pull request ----------------------------------------

PUBLISH = ROOT / "skills/evidence/scripts/publish"
EVIDENCE_CHECK = ROOT / "skills/evidence/scripts/pr-evidence-check"


def _with_origin(tmp_path, name="origin.git"):
    bare = tmp_path / name
    bare.mkdir()
    git(bare, "init", "-q", "--bare")
    r = repo(tmp_path)
    git(r, "remote", "add", "origin", str(bare))
    return r, bare


def _fake_gh(tmp_path, body):
    """A gh that serves `pr view` from a file and stores what `pr edit --body-file` is given."""
    bin_dir = tmp_path / "ghbin"
    bin_dir.mkdir(exist_ok=True)
    (tmp_path / "gh-body.txt").write_text(body)
    (bin_dir / "gh").write_text(
        "#!/usr/bin/env python3\nimport json, sys, pathlib\na = sys.argv[1:]\nbase = pathlib.Path(__file__).parent.parent\n"
        "if a[:2] == ['pr', 'view']:\n    body = (base / 'gh-body.txt').read_text()\n"
        "    print(json.dumps({'body': body, 'comments': []}) if '--json' in a and 'body,comments' in a else body)\n"
        "elif a[:2] == ['pr', 'edit']:\n    (base / 'gh-edited.txt').write_text(pathlib.Path(a[a.index('--body-file') + 1]).read_text())\n")
    (bin_dir / "gh").chmod(0o755)
    return {"PATH": f"{bin_dir}:{os.environ['PATH']}"}


def test_publish_shows_the_screenshots_from_a_branch_that_is_not_the_change(tmp_path):
    """2026-11: 103 of 214 UI pull requests said the screenshots were under .artifacts/ (not in git); 3 showed one."""
    r, bare = _with_origin(tmp_path)
    shots = r / ".artifacts" / "T-1"
    shots.mkdir(parents=True)
    (shots / "01-start.png").write_bytes(b"png1")
    (shots / "02-end.png").write_bytes(b"png2")
    (shots / "clip.mov").write_bytes(b"mov")
    (shots / "notes.txt").write_text("not an image")
    (shots / "huge.png").write_bytes(b"x" * 3000)
    head = subprocess.run(["git", "-C", str(r), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    done = run([PUBLISH, "T-1", "--repo", r, "--web-base", "https://example.test/o/r", "--max-mb", "0.001"], cwd=tmp_path)
    assert done.returncode == 0, (done.stdout, done.stderr)
    commit = subprocess.run(["git", "-C", str(bare), "rev-parse", "jstack-evidence"], capture_output=True, text=True).stdout.strip()
    assert f"![01-start](https://example.test/o/r/blob/{commit}/T-1/{head}/01-start.png?raw=true)" in done.stdout
    assert f"[clip (video)](https://example.test/o/r/blob/{commit}/T-1/{head}/clip.mov?raw=true)" in done.stdout
    assert "notes.txt" not in done.stdout and "huge.png" not in done.stdout and "skipped huge.png" in done.stderr
    tree = subprocess.run(["git", "-C", str(bare), "ls-tree", "-r", "--name-only", "jstack-evidence"], capture_output=True, text=True).stdout
    assert f"T-1/{head}/02-end.png" in tree.splitlines()
    branches = subprocess.run(["git", "-C", str(r), "branch", "--list"], capture_output=True, text=True).stdout
    assert "jstack-evidence" not in branches and subprocess.run(["git", "-C", str(r), "diff", "--cached", "--quiet"]).returncode == 0, \
        "the repo's own branches and index are not touched"
    again = run([PUBLISH, "T-1", "--repo", r, "--web-base", "https://example.test/o/r", "--max-mb", "0.001"], cwd=tmp_path)
    assert subprocess.run(["git", "-C", str(bare), "rev-parse", "jstack-evidence"], capture_output=True, text=True).stdout.strip() == commit, \
        "the same files published twice make no second commit"
    other = r / ".artifacts" / "T-2"
    other.mkdir()
    (other / "a.png").write_bytes(b"other")
    assert run([PUBLISH, "T-2", "--repo", r, "--web-base", "https://example.test/o/r"], cwd=tmp_path).returncode == 0
    tree = subprocess.run(["git", "-C", str(bare), "ls-tree", "-r", "--name-only", "jstack-evidence"], capture_output=True, text=True).stdout
    assert f"T-1/{head}/01-start.png" in tree and f"T-2/{head}/a.png" in tree, "a later ticket keeps the earlier ones"
    assert again.returncode == 0


def test_publish_does_not_pretend_when_the_origin_cannot_serve_images_or_there_is_nothing(tmp_path):
    r, bare = _with_origin(tmp_path)
    assert run([PUBLISH, "T-9", "--repo", r], cwd=tmp_path).returncode == 1, "no .artifacts folder for the ticket"
    shots = r / ".artifacts" / "T-9"
    shots.mkdir(parents=True)
    assert run([PUBLISH, "T-9", "--repo", r], cwd=tmp_path).returncode == 1, "a folder with no images"
    (shots / "a.png").write_bytes(b"x")
    local = run([PUBLISH, "T-9", "--repo", r], cwd=tmp_path)           # a bare repo on disk is not a web address
    assert local.returncode == 2 and "stay local" in local.stderr and "a.png" in local.stderr, (local.stdout, local.stderr)
    assert subprocess.run(["git", "-C", str(bare), "branch", "--list"], capture_output=True, text=True).stdout.strip() == "", \
        "nothing was pushed"


def test_publish_replaces_its_block_in_the_pull_request_description(tmp_path):
    r, _ = _with_origin(tmp_path)
    shots = r / ".artifacts" / "T-3"
    shots.mkdir(parents=True)
    (shots / "01.png").write_bytes(b"x")
    old = "Fixes the pill.\n\n<!-- jstack-evidence:begin -->\nOLD BLOCK\n<!-- jstack-evidence:end -->\n\nCross-review: none\n"
    env = _fake_gh(tmp_path, old)
    done = run([PUBLISH, "T-3", "--repo", r, "--pr", "12", "--web-base", "https://example.test/o/r"], cwd=tmp_path, env=env)
    assert done.returncode == 0, done.stderr
    edited = (tmp_path / "gh-edited.txt").read_text()
    assert "OLD BLOCK" not in edited and edited.count("jstack-evidence:begin") == 1
    assert "Fixes the pill." in edited and "Cross-review: none" in edited, "the rest of the description is kept"
    assert "![01](https://example.test/o/r/blob/" in edited


def _ui_branch(tmp_path, ui_paths="app/**/*.tsx", file="app/Button.tsx"):
    r = repo(tmp_path, f"# P\n\n## jstack settings\nintegration_branch: main\nui_paths: {ui_paths}\n")
    git(r, "checkout", "-q", "-b", "feat")
    (r / file).parent.mkdir(parents=True, exist_ok=True)
    (r / file).write_text("export const Button = () => null\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "change")
    return r


def test_a_ui_change_needs_a_screenshot_the_reviewer_can_open(tmp_path):
    r = _ui_branch(tmp_path)
    body = tmp_path / "body.md"
    check = lambda text: (body.write_text(text), run([EVIDENCE_CHECK, "--repo", r, "--base", "main", "--body-file", body], cwd=tmp_path))[1]
    for nothing in ("Fixes the pill.", "Screenshots are under `.artifacts/LOUD-432` (not in git).",
                    "![](.artifacts/T/01.png)", "| [smally](https://vercel.com/x) | ![Ready](https://vercel.com/static/status/ready.svg) |",
                    "![build](https://img.shields.io/badge/build-passing-green)"):
        bad = check(nothing)
        assert bad.returncode == 1 and "shows no screenshot" in bad.stderr, (nothing, bad.stdout, bad.stderr)
    for shown in ("![a](https://example.test/o/r/blob/abc/T/1.png?raw=true)",
                  '<img width="300" src="https://github.com/user-attachments/assets/abc-123">',
                  "[clip](https://example.test/x/demo.mp4)"):
        ok = check(shown)
        assert ok.returncode == 0 and "ok," in ok.stdout, (shown, ok.stdout, ok.stderr)


def test_the_screenshot_check_only_applies_to_ui_changes_and_when_the_gate_is_on(tmp_path):
    body = tmp_path / "body.md"
    body.write_text("nothing to see")
    docs = _ui_branch(tmp_path, file="docs/readme.md")
    done = run([EVIDENCE_CHECK, "--repo", docs, "--base", "main", "--body-file", body], cwd=tmp_path)
    assert done.returncode == 0 and "nothing to show" in done.stdout, (done.stdout, done.stderr)
    (tmp_path / "off").mkdir()
    off = _ui_branch(tmp_path / "off", ui_paths="")
    done = run([EVIDENCE_CHECK, "--repo", off, "--base", "main", "--body-file", body], cwd=tmp_path)
    assert done.returncode == 0 and "off" in done.stdout


def test_the_screenshot_check_reads_the_pull_request_and_its_comments(tmp_path):
    r = _ui_branch(tmp_path)
    env = _fake_gh(tmp_path, "![a](https://example.test/x.png)")
    done = run([EVIDENCE_CHECK, "--repo", r, "--base", "main", "--pr", "7"], cwd=tmp_path, env=env)
    assert done.returncode == 0 and "ok," in done.stdout, (done.stdout, done.stderr)
    env = _fake_gh(tmp_path, "no pictures here")
    assert run([EVIDENCE_CHECK, "--repo", r, "--base", "main", "--pr", "7"], cwd=tmp_path, env=env).returncode == 1
