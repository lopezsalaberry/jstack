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
PROBE = ROOT / "skills/wave/scripts/quota-probe"
WAVE = ROOT / "skills/wave/scripts/wave-status"
PRWAIT = ROOT / "skills/ticket/scripts/pr-wait"
PROOFVALID = ROOT / "skills/ticket/scripts/proof-valid"
CHECKLIST = ROOT / "skills/ticket/scripts/checklist-init"
TOKENLINT = ROOT / "skills/ticket/scripts/token-lint"
CHECK = ROOT / "skills/ticket/scripts/check"
BRIEF = ROOT / "skills/wave/scripts/brief"
PUBLISH = ROOT / "skills/ticket/scripts/publish"
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
    r = repo(tmp_path, "# P\n\n## jstack settings\nintegration_branch: develop\nreviewer_models: a:m1, b:m2  # order matters\n"
                       "max_parallel: 4\n\n## Other\nmax_parallel: 999\n")
    out = json.loads(run([SETTINGS, "--repo", r, "--json"], cwd=tmp_path).stdout)
    assert out["integration_branch"] == "develop"
    assert out["reviewer_models"] == "a:m1, b:m2"  # inline comment stripped
    assert out["max_parallel"] == "4"             # a later heading does not leak in
    assert out["verify_mode"] == "visible" and out["routing"] == ""
    env = run([SETTINGS, "--repo", r, "max_parallel"], cwd=tmp_path, env={"JSTACK_MAX_PARALLEL": "5"})
    assert env.stdout.strip() == "5"


def test_settings_without_a_block_use_defaults_and_unknown_keys_fail(tmp_path):
    r = repo(tmp_path)
    assert run([SETTINGS, "--repo", r, "integration_branch"], cwd=tmp_path).stdout.strip() == "main"
    assert run([SETTINGS, "--repo", r, "quota_probe"], cwd=tmp_path).stdout.strip().endswith("wave/scripts/quota-probe")
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
    fine = tmp_path / "fine-probe"                           # a configured probe that knows nothing about marks
    fine.write_text("#!/usr/bin/env python3\nimport sys\nprint('configured', *sys.argv[1:])\nsys.exit(0)\n")
    fine.chmod(0o755)
    env = {"JSTACK_QUOTA_PROBE": str(fine), "JSTACK_QUOTA_MARKS": str(tmp_path / "marks.txt")}
    marked = run([PROBE, "--mark-exhausted", "alpha", "--minutes", "5"], cwd=tmp_path, env=env)
    assert "marked exhausted" in marked.stdout and "configured" not in marked.stdout, "marks are kept here, not handed off"
    refused = run([PROBE, "--provider", "alpha"], cwd=tmp_path, env=env)
    assert refused.returncode == 1 and "configured" not in refused.stdout, "a mark answers before the configured probe is asked"
    other = run([PROBE, "--provider", "beta"], cwd=tmp_path, env=env)
    assert other.returncode == 0 and other.stdout.strip() == "configured --provider beta", "only the reading is handed off"
    assert run([PROBE, "--clear", "alpha"], cwd=tmp_path, env=env).returncode == 0
    assert run([PROBE, "--provider", "alpha"], cwd=tmp_path, env=env).stdout.strip() == "configured --provider alpha"
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
    assert bad.returncode == 64 and "expected" in bad.stderr, "exit 2 would mean 'unknown, go ahead'"
    src.write_text("not-a-row\nalpha acct1 0\n")
    assert run([PROBE, "--source", src, "--provider", "alpha"], cwd=tmp_path).returncode == 64, "the 0% line below a bad one is never reached"


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
    far = time.strftime("%Y-%m-%d", time.localtime(time.time() + 400 * 86400))            # a mistyped year
    for text, why in (("2020-01-01", "already past"), (far, "days away"), ("tomorrow-ish", "not an ISO")):
        bad = run([PROBE, "--mark-exhausted", "x", "--until", text], cwd=tmp_path, env=marks)
        assert bad.returncode == 64 and why in bad.stderr, (text, bad.stderr)   # 64, never the 2 that means "unknown"
    both = run([PROBE, "--mark-exhausted", "x", "--minutes", "5", "--until", later], cwd=tmp_path, env=marks)
    assert both.returncode == 64 and "exclusive" in both.stderr
    epoch = run([PROBE, "--mark-exhausted", "y", "--until", str(int(time.time()) + 7200)], cwd=tmp_path, env=marks)
    assert epoch.returncode == 0, "epoch seconds are accepted too"
    assert run([PROBE, "--mark-exhausted", "z"], cwd=tmp_path, env=marks).stdout.strip().endswith("for 60 min")
    next_reset = time.strftime("%Y-%m-%d", time.localtime(time.time() + 48 * 86400))      # a reset on the 1st, 48 days out
    assert run([PROBE, "--mark-exhausted", "w", "--until", next_reset], cwd=tmp_path, env=marks).returncode == 0


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
                    "max_parallel: 3\n")
    r = repo(tmp_path, "# P\n\n## jstack settings\nmax_parallel: 7\n")
    env = {"JSTACK_USER_SETTINGS": str(user)}
    out = json.loads(run([SETTINGS, "--repo", r, "--json"], cwd=tmp_path, env=env).stdout)
    assert out["reviewer_models"] == "codex, cursor, auto"        # from the operator's file, inline comment stripped
    assert out["routing"] == "UI and UX work: the strongest model"
    assert out["max_parallel"] == "7"                             # the repo's value replaces the operator's
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
    _shutil.copytree(ROOT / "templates", spaced / "templates")
    r = repo(tmp_path)
    probe = run([spaced / "skills/jstack/scripts/jstack-settings", "--repo", r, "quota_probe"], cwd=tmp_path).stdout.strip()
    import shlex as _shlex
    assert _shlex.split(probe)[0].endswith("Crucial X9/base/skills/wave/scripts/quota-probe"), probe
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
    scripts = [p for d in ("skills", "extras") for p in ROOT.glob(f"{d}/*/scripts/*") if p.is_file()]
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


def test_a_configured_probe_only_has_to_answer_provider(tmp_path):
    """The shipped quota-probe keeps the refusal marks, so a probe of your own answers one question."""
    fake = _fake_probe(tmp_path, "import sys\nif sys.argv[1:2] == ['--provider']:\n    sys.exit(2)\nsys.stderr.write('usage: fake [--provider NAME]\\n')\nsys.exit(2)\n")
    done = _doctor_with_probe(tmp_path, fake)
    assert "ok   quota_probe runs" in done.stdout and done.returncode == 0, done.stdout


def test_doctor_leaves_the_real_marks_file_alone(tmp_path):
    """The doctor asks about a throwaway provider name and writes no mark."""
    marks = tmp_path / "real-marks.txt"
    marks.write_text("claude 4102444800 keep me\n")
    r = repo(tmp_path)
    done = run([DOCTOR, "--repo", r], cwd=tmp_path, env={"JSTACK_QUOTA_MARKS": str(marks)})
    assert "ok   quota_probe runs" in done.stdout, done.stdout
    assert marks.read_text() == "claude 4102444800 keep me\n"


# --- the UI gate, the rules card and the version, as the doctor reports them ----------------------

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


def test_doctor_says_when_no_file_an_agent_reads_has_the_current_card(tmp_path):
    """A rule is followed only if it is read. 2026-11-10: three of five repos carried an old copy of the rules and nothing
    said so. The card may sit in the repo or in a file the harness loads for every repo."""
    current = TEMPLATE.read_text()
    r = repo(tmp_path, current)
    path = {"PATH": str(tools_dir(tmp_path, True))}
    doctor = lambda: run([DOCTOR, "--repo", r], cwd=tmp_path, env=path).stdout
    assert "ok   rules card: current, in" in doctor()
    (r / "AGENTS.md").write_text(current.replace("**One gate.**", "**One gate, usually.**"))
    assert "warn rules card:" in doctor() and "older or edited card" in doctor()
    (r / "AGENTS.md").write_text("# P\n\n## jstack settings\nmodels: a:b\nui_paths:\n")
    out = doctor()
    assert "warn rules card: no file an agent reads here carries the rules card" in out
    assert "warn settings this version does not read: models" in out
    user = tmp_path / ".claude" / "CLAUDE.md"                    # HOME is the working directory in these tests
    user.parent.mkdir()
    user.write_text("# My notes\n\n" + current.split("## jstack settings")[0])
    assert f"ok   rules card: current, in {user}" in doctor()


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


# --- the before and after, where the reader of the pull request sees them ------------------------

def _out(*cmd, cwd=None):
    return subprocess.run(list(map(str, cmd)), cwd=cwd, capture_output=True, text=True).stdout.strip()


def _with_origin(tmp_path, agents=""):
    """A repo on a branch `feat` with one commit over `main`, and a bare `origin` that has `main`."""
    bare = tmp_path / "origin.git"
    bare.mkdir()
    git(bare, "init", "-q", "--bare")
    r = repo(tmp_path, agents)
    git(r, "remote", "add", "origin", str(bare))
    git(r, "push", "-q", "origin", "main")
    git(r, "checkout", "-q", "-b", "feat")
    (r / "change.txt").write_text("one\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "change")
    return r, bare


def _fake_gh(tmp_path, pr):
    """A gh that serves `pr view` from a dict and stores what `pr edit --body-file` is given."""
    bin_dir = tmp_path / "ghbin"
    bin_dir.mkdir(exist_ok=True)
    (tmp_path / "gh-pr.json").write_text(json.dumps(pr))
    (bin_dir / "gh").write_text(
        "#!/usr/bin/env python3\nimport json, sys, pathlib\na = sys.argv[1:]\nbase = pathlib.Path(__file__).parent.parent\n"
        "data = json.loads((base / 'gh-pr.json').read_text())\n"
        "if a[:2] == ['pr', 'view']:\n    print(data['body'] if '-q' in a else json.dumps(data))\n"
        "elif a[:2] == ['pr', 'edit']:\n    (base / 'gh-edited.txt').write_text(pathlib.Path(a[a.index('--body-file') + 1]).read_text())\n")
    (bin_dir / "gh").chmod(0o755)
    return {"PATH": f"{bin_dir}:{os.environ['PATH']}"}


WEB = "https://example.test/o/r"


def test_publish_builds_a_before_and_after_table_in_a_ref_nobody_fetches(tmp_path):
    """Two weeks of four repos: 103 of 214 UI pull requests said "screenshots are under .artifacts/" and showed nothing.
    Real evidence folders averaged 10 MB a ticket, so the folder is not what gets published, and not to a branch."""
    r, bare = _with_origin(tmp_path)
    shots = r / ".artifacts" / "T-1"
    shots.mkdir(parents=True)
    for name in ("before-start.png", "after-start.png", "after-new-panel.png", "01-raw-capture.png", "notes.md"):
        (shots / name).write_bytes(name.encode())
    (shots / "before.txt").write_text("FAILED 1\n")
    (shots / "after.txt").write_text("passed 1\n")
    head, base = _out("git", "-C", r, "rev-parse", "HEAD"), _out("git", "-C", r, "rev-parse", "main")
    done = run([PUBLISH, "T-1", "--repo", r, "--web-base", WEB, "--base", "main", "--not-shown", "Safari was not tried"], cwd=tmp_path)
    assert done.returncode == 0, (done.stdout, done.stderr)
    commit = _out("git", "-C", bare, "rev-parse", "refs/jstack-evidence/T-1")
    at = f"{WEB}/blob/{commit}/{head[:10]}"
    assert f"| | Before: [{base[:10]}]({WEB}/commit/{base}) | After: [{head[:10]}]({WEB}/commit/{head}) |" in done.stdout
    assert f"| start | ![Before: start]({at}/before-start.png?raw=true) | ![After: start]({at}/after-start.png?raw=true) |" in done.stdout
    assert f"| new panel | (new) | ![After: new panel]({at}/after-new-panel.png?raw=true) |" in done.stdout
    assert f"| Output | [before.txt]({at}/before.txt) | [after.txt]({at}/after.txt) |" in done.stdout
    assert "**Not shown:** Safari was not tried" in done.stdout
    assert "raw-capture" not in done.stdout and "notes" not in done.stdout, "only the named files are published"
    assert _out("git", "-C", bare, "for-each-ref", "--format=%(refname)") .splitlines() == ["refs/heads/main", "refs/jstack-evidence/T-1"]
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", f"file://{bare}", str(clone)], check=True, capture_output=True)   # file:// uses the real transport
    assert subprocess.run(["git", "-C", str(clone), "cat-file", "-e", commit], capture_output=True).returncode != 0, \
        "a normal clone does not download the pictures"
    assert "jstack-evidence" not in _out("git", "-C", r, "for-each-ref") and subprocess.run(["git", "-C", str(r), "diff", "--cached", "--quiet"]).returncode == 0, \
        "the repo's own refs and index are not touched"
    assert run([PUBLISH, "T-1", "--repo", r, "--web-base", WEB, "--base", "main"], cwd=tmp_path).returncode == 0
    assert _out("git", "-C", bare, "rev-parse", "refs/jstack-evidence/T-1") == commit, "the same files twice make no second commit"
    (r / "change.txt").write_text("two\n")
    git(r, "commit", "-q", "-am", "more")
    (shots / "after-start.png").write_bytes(b"newer")
    assert run([PUBLISH, "T-1", "--repo", r, "--web-base", WEB, "--base", "main"], cwd=tmp_path).returncode == 0
    assert _out("git", "-C", bare, "rev-parse", "refs/jstack-evidence/T-1^") == commit, "a later run adds to the ref, so earlier links keep working"
    tree = _out("git", "-C", bare, "ls-tree", "-r", "--name-only", "refs/jstack-evidence/T-1")
    assert f"{head[:10]}/after-start.png" in tree and f"{_out('git', '-C', r, 'rev-parse', 'HEAD')[:10]}/after-start.png" in tree


def test_publish_refuses_the_folder_a_big_file_and_an_origin_nobody_can_open(tmp_path):
    r, bare = _with_origin(tmp_path)
    publish = lambda *a: run([PUBLISH, "T-9", "--repo", r, "--base", "main", *a], cwd=tmp_path)
    assert publish("--web-base", WEB).returncode == 1, "no .artifacts folder for the ticket"
    shots = r / ".artifacts" / "T-9"
    shots.mkdir(parents=True)
    (shots / "01.png").write_bytes(b"x")
    unnamed = publish("--web-base", WEB)
    assert unnamed.returncode == 1 and "before-<state>.png" in unnamed.stderr, "a capture with no before- or after- name says nothing"
    (shots / "after-a.png").write_bytes(b"x" * 3000)
    big = publish("--web-base", WEB, "--max-mb", "0.001")
    assert big.returncode == 2 and "after-a.png" in big.stderr and "over" in big.stderr
    for i in range(9):
        (shots / f"after-s{i}.png").write_bytes(b"x")
    many = publish("--web-base", WEB)
    assert many.returncode == 2 and "limit 8" in many.stderr, "the folder is not what gets published"
    for i in range(9):
        (shots / f"after-s{i}.png").unlink()
    local = publish()                                           # a bare repo on disk is not a web address
    assert local.returncode == 2 and "stay local" in local.stderr and "after-a.png" in local.stderr, (local.stdout, local.stderr)
    assert "jstack-evidence" not in _out("git", "-C", bare, "for-each-ref"), "nothing was pushed by any refused run"
    assert run([PUBLISH, "../x", "--repo", r], cwd=tmp_path).returncode == 2, "a ticket name is not a path"


def test_publish_replaces_its_block_in_the_pull_request_and_leaves_a_todo_for_what_is_not_shown(tmp_path):
    r, _ = _with_origin(tmp_path)
    shots = r / ".artifacts" / "T-3"
    shots.mkdir(parents=True)
    (shots / "after-list.png").write_bytes(b"x")
    old = "Fixes the pill.\n\n<!-- jstack-evidence:begin -->\nOLD BLOCK\n<!-- jstack-evidence:end -->\n\n## Tests\n3 passed\n"
    env = _fake_gh(tmp_path, {"body": old})
    done = run([PUBLISH, "T-3", "--repo", r, "--pr", "12", "--web-base", WEB, "--base", "main"], cwd=tmp_path, env=env)
    assert done.returncode == 0, done.stderr
    edited = (tmp_path / "gh-edited.txt").read_text()
    assert "OLD BLOCK" not in edited and edited.count("jstack-evidence:begin") == 1
    assert "Fixes the pill." in edited and "## Tests\n3 passed" in edited, "the rest of the description is kept"
    assert "![After: list](" in edited and "**Not shown:** TODO" in edited


# --- check: the merge gate as one command ---------------------------------------------------

def _proven_ticket(tmp_path, file="app/button.css", text=".btn { color: #3366ff; }\n"):
    """A repo whose branch `feat` changes one file over `main`, with a stamped checklist that has one PASS row."""
    r = repo(tmp_path, "# P\n\n## jstack settings\nintegration_branch: main\nui_paths: app/**/*.css\n")
    (r / "design").mkdir()
    (r / "design/tokens.json").write_text(json.dumps({"color": {"brand": {"$value": "#3366ff"}}}))
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "tokens")
    git(r, "checkout", "-q", "-b", "feat")
    assert run([CHECKLIST, "T-1", "--base", "main"], cwd=r).returncode == 0
    (r / file).parent.mkdir(parents=True, exist_ok=True)
    (r / file).write_text(text)
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "change")
    return r


def _row(r, row, stamp=True):
    """Put one row in the checklist's table (replacing the previous one) and stamp it."""
    path = r / ".artifacts/T-1/checklist.md"
    lines = [l for l in path.read_text().splitlines() if not (l.startswith("| ") and not l.startswith("| Target"))]
    at = next(i for i, l in enumerate(lines) if l.startswith("|---"))
    path.write_text("\n".join(lines[:at + 1] + [row] + lines[at + 1:]) + "\n")
    if stamp:
        assert run([PROOFVALID, "--stamp", path, "--base", "main"], cwd=r).returncode == 0


def _check(r, *args, env=None):
    done = run([CHECK, "T-1", "--base", "main", *args], cwd=r, env=env)
    return done.returncode, {line.split(":")[0]: line for line in done.stdout.splitlines()}, done.stdout


def test_check_passes_a_proven_change_and_names_what_is_missing(tmp_path):
    r = _proven_ticket(tmp_path)
    code, lines, out = _check(r)
    assert code == 1 and "FAIL proof" in lines and "proof-valid --stamp" in lines["FAIL proof"], out   # nothing stamped yet
    _row(r, "| the button is blue | PASS | 4 | ran the page | after.txt |")
    code, lines, out = _check(r)
    assert code == 0 and out.splitlines()[-1].startswith("check: ok"), out
    for name in ("PASS branch", "PASS clean tree", "PASS up to date", "PASS proof", "PASS design", "SKIP pull request"):
        assert name in lines, (name, out)
    _row(r, "| the button is blue | PASS | 3 | read the code | - |")
    code, lines, out = _check(r)
    assert code == 1 and "without level 4 or 5" in lines["FAIL proof"], "a PASS nobody ran is not a pass"
    _row(r, "| the button is blue | FAIL | 5 | still grey | after.png |")
    assert "not PASS" in _check(r)[1]["FAIL proof"]
    for not_a_pass in ("| it saves the note | unproven (level 1) | 1 | I said so | - |",          # found by an independent review:
                       "| it saves the note | PASS | 1 to 5 | copied the hint | - |"):             # both of these passed the gate
        _row(r, not_a_pass)
        assert _check(r)[0] == 1 and "FAIL proof" in _check(r)[1], not_a_pass
    _row(r, "| the button is blue | **PASS** | 5 | saw it | after.png |")
    assert _check(r)[0] == 0, "bold is still a pass"
    _row(r, "| <the thing the ticket asks for> | PASS or FAIL | 1 to 5 | <command> | <file> |")
    assert "no filled row" in _check(r)[1]["FAIL proof"], "the template row is not proof"
    assert run([CHECK, "--base", "main"], cwd=r).stdout.count("proof") == 1, "with one checklist the ticket may be left out"
    assert "FAIL proof: no .artifacts/NOPE/checklist.md" in run([CHECK, "NOPE", "--base", "main"], cwd=r).stdout


def test_check_fails_an_edited_change_an_off_token_color_and_a_branch_that_is_not_ready(tmp_path):
    r = _proven_ticket(tmp_path)
    _row(r, "| the button is blue | PASS | 5 | saw it | after-button.png |")
    assert _check(r)[0] == 0
    (r / "app/button.css").write_text(".btn { color: #ff0000; }\n")
    code, lines, out = _check(r)
    assert code == 1 and "uncommitted" in lines["FAIL clean tree"], out
    git(r, "commit", "-q", "-am", "redder")
    code, lines, out = _check(r)
    assert "the patch changed since the proof" in lines["FAIL proof"], out
    assert "FAIL design" in lines and "is not a design token" in lines["FAIL design"], out
    git(r, "checkout", "-q", "--detach")
    assert "detached HEAD" in _check(r)[1]["FAIL branch"]
    git(r, "checkout", "-q", "main")
    code, lines, out = _check(r)
    assert "integration branch" in lines["FAIL branch"] and "adds nothing over main" in lines["FAIL change"], out
    (r / "other.txt").write_text("moved on\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "main moved")
    git(r, "checkout", "-q", "feat")
    assert "rebase" in _check(r)[1]["FAIL up to date"]
    assert run([CHECK, "T-1", "--base", "no/such"], cwd=r).stdout.count("FAIL up to date: no/such does not exist") == 1
    assert run([CHECK], cwd=tmp_path).returncode == 2, "outside a repo is a usage error, not a verdict"


def test_check_reads_the_pull_request_head_screenshot_review_ci_and_mergeability(tmp_path):
    r = _proven_ticket(tmp_path)
    _row(r, "| the button is blue | PASS | 5 | saw it | after-button.png |")
    head = _out("git", "-C", r, "rev-parse", "HEAD")
    patch = re.search(r"Patch-id: (\S+)", run([PROOFVALID, "--print", "--base", "main"], cwd=r).stdout).group(1)
    shown = f"![After: button]({WEB}/blob/abc/after-button.png?raw=true)\n\n**Not shown:** dark mode\n"
    review = f"Review: verify by model-x | independence L1 | verdict PASS | patch {patch}\n"
    green = [{"name": "ci", "status": "COMPLETED", "conclusion": "SUCCESS"}]

    def check(body, **pr):
        data = {"body": body, "comments": [], "statusCheckRollup": green, "mergeable": "MERGEABLE", "reviewDecision": "", "headRefOid": head, **pr}
        return _check(r, "--pr", "7", env=_fake_gh(tmp_path, data))

    code, lines, out = check(shown + review)
    assert code == 0 and all(f"PASS {n}" in lines for n in ("head", "screenshot", "review", "ci", "mergeable")), out
    assert "FAIL head" in check(shown + review, headRefOid="0" * 40)[1], "the PR must be at the head that was checked"
    for nothing in ("Fixes it.", "Screenshots are under `.artifacts/T-1` (not in git).", "![](.artifacts/T-1/after.png)",
                    "![shot](https://example.com/not-a-picture)",
                    "![build](https://img.shields.io/badge/build-passing-green.png)",
                    "| [app](https://vercel.com/x) | ![Ready](https://vercel.com/static/status/ready.svg) |"):
        assert "shows no picture" in check(nothing + "\n" + review)[1]["FAIL screenshot"], nothing
    assert 'TODO under "Not shown"' in check(shown.replace("dark mode", "TODO: say what this proof does not cover") + review)[1]["FAIL screenshot"]
    assert "no `Review:` line" in check(shown)[1]["FAIL review"], "a UI change needs someone else's verdict"
    assert "says CHANGES" in check(shown + review.replace("verdict PASS", "verdict CHANGES"))[1]["FAIL review"]
    assert "older patch" in check(shown + review.replace(patch, "f" * 40))[1]["FAIL review"]
    assert "no `patch <id>`" in check(shown + "Review: verify by me | verdict PASS\n")[1]["FAIL review"], "a verdict tied to nothing"
    assert "PASS screenshot" in check('<img width="300" src="https://github.com/user-attachments/assets/abc-123">\n**Not shown:** x\n' + review)[1]
    assert "has not said yet" in check(shown + review, mergeable="UNKNOWN")[1]["FAIL mergeable"]
    assert "failed: ci" in check(shown + review, statusCheckRollup=[{"name": "ci", "status": "COMPLETED", "conclusion": "FAILURE"}])[1]["FAIL ci"]
    assert "still running" in check(shown + review, statusCheckRollup=[{"name": "ci", "status": "IN_PROGRESS", "conclusion": None}])[1]["FAIL ci"]
    assert "SKIP ci" in check(shown + review, statusCheckRollup=[])[1]
    assert "conflicts" in check(shown + review, mergeable="CONFLICTING")[1]["FAIL mergeable"]
    assert "requests changes" in check(shown + review, reviewDecision="CHANGES_REQUESTED")[1]["FAIL mergeable"]


def test_check_asks_nothing_about_screens_of_a_change_with_no_ui_file(tmp_path):
    r = _proven_ticket(tmp_path, file="server/api.py", text="x = 1\n")
    _row(r, "| the api answers | PASS | 4 | ran the test | after.txt |")
    data = {"body": "Fixes it.", "comments": [], "statusCheckRollup": [], "mergeable": "MERGEABLE", "reviewDecision": "",
            "headRefOid": _out("git", "-C", r, "rev-parse", "HEAD")}
    code, lines, out = _check(r, "--pr", "7", env=_fake_gh(tmp_path, data))
    assert code == 0 and "SKIP design" in lines and "SKIP screenshot" in lines and "SKIP review" in lines, out
    assert "high-risk or user-visible" in lines["SKIP review"], "the gate says what it cannot know"
    (r / "AGENTS.md").write_text("# P\n\n## jstack settings\nintegration_branch: main\nverify_mode: always\n")
    git(r, "commit", "-q", "-am", "always")
    _row(r, "| the api answers | PASS | 4 | ran the test | after.txt |")
    data["headRefOid"] = _out("git", "-C", r, "rev-parse", "HEAD")
    assert "FAIL review" in _check(r, "--pr", "7", env=_fake_gh(tmp_path, data))[1], "`verify_mode: always` asks for a verdict on every change"


# --- brief: what a worker is told does not depend on memory -----------------------------------

def _brief(r, *args):
    return run([BRIEF, "T-7", "--repo", r, "--goal", "Make the button blue", "--done-when", "the button is blue on the home page", *args], cwd=r)


def test_brief_writes_a_brief_that_stands_alone_and_will_not_run_without_a_model(tmp_path):
    """Of 143 sessions, the ones whose brief asked for the flow followed it 97% of the time; the others, 20%."""
    r = repo(tmp_path, "# P\n\n## jstack settings\nintegration_branch: develop\nui_paths: app/**/*.css\n")
    done = _brief(r, "--touches", "server/api.py, server/db.py", "--model", "model-x", "--effort", "low")
    assert done.returncode == 0, done.stderr
    for needed in ("Ticket T-7: Make the button blue", "Integration branch: develop.", "Touches: server/api.py, server/db.py.",
                   "Done when: the button is blue on the home page", "`ticket` skill", "`checklist-init T-7`", "`check T-7 --pr <number>`",
                   "Merge the PR into develop", "Do not ask the user anything", "report WAITING",
                   "INTEGRATED <sha>, READY_FOR_INTEGRATOR, WAITING <condition> or BLOCKED(env|task|decision)", "what you did not verify"):
        assert needed in done.stdout, needed
    assert "Design:" not in done.stdout, "a ticket that touches no UI file gets no design block"
    assert "start this worker on model-x at effort low" in done.stderr
    ready = _brief(r, "--touches", "server/api.py", "--model", "m", "--effort", "low", "--stop-before-merge", "--note", "continue from RUNSTATE.md at abc")
    assert "Do not merge." in ready.stdout and "Merge the PR into" not in ready.stdout and "- continue from RUNSTATE.md at abc" in ready.stdout
    missing = _brief(r, "--touches", "server/api.py", "--effort", "low")
    assert missing.returncode == 2 and missing.stdout == "", "a delegate that is not told its model inherits its parent's"
    assert _brief(r, "--touches", " ", "--model", "m", "--effort", "low").returncode == 2, "a ticket with no files is not ready to launch"


def test_brief_adds_the_design_block_when_the_ticket_may_touch_ui(tmp_path):
    r = repo(tmp_path, "# P\n\n## jstack settings\nui_paths: app/**/*.css, **/*.tsx\ndesign_tokens: design/tokens.json\n")
    for name in ("app/button.css", "web/Home.tsx", "server/api.py", "docs/readme.md"):
        (r / name).parent.mkdir(exist_ok=True)
        (r / name).write_text("x\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "files")
    block = lambda touches: "Design:" in _brief(r, "--touches", touches, "--model", "m", "--effort", "low").stdout
    assert block("app/button.css") and block("app/") and block("app/**") and block("web/") and block("new/Panel.tsx")
    assert not block("server/"), "a folder with no UI file is not a UI ticket, whatever the glob starts with"
    assert not block("docs/readme.md") and not block("server/api.py, server/db.py")
    text = _brief(r, "--touches", "app/button.css", "--model", "m", "--effort", "low")
    assert "design/tokens.json" in text.stdout and "`before-<state>.png`" in text.stdout and "`publish T-7 --pr <number>`" in text.stdout
    assert "the design block is included" in text.stderr
    (tmp_path / "plain").mkdir()
    plain = repo(tmp_path / "plain")
    assert "Design:" not in _brief(plain, "--touches", "app/x.css", "--model", "m", "--effort", "low").stdout, \
        "with `ui_paths` empty the design gate is off"


def test_wave_status_shows_no_metric_cell_when_runstate_has_none(tmp_path):
    r = repo(tmp_path)
    (r / "RUNSTATE.md").write_text("Status: WAITING probe exits 0\nDone when: tests pass\nNext step: rerun the tests\n")
    out = run([WAVE, "--repo", r], cwd=tmp_path).stdout
    assert "?" not in out.replace("ago", "") and "| WAITING probe exits 0 |  | rerun the tests |" in out, out


def test_publish_dry_run_needs_no_origin(tmp_path):
    r = repo(tmp_path)
    git(r, "checkout", "-q", "-b", "feat")
    (r / "x.txt").write_text("x\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "x")
    shots = r / ".artifacts" / "T-1"
    shots.mkdir(parents=True)
    (shots / "after-home.png").write_bytes(b"x")
    dry = run([PUBLISH, "T-1", "--repo", r, "--dry-run", "--base", "main", "--web-base", WEB], cwd=tmp_path)
    assert dry.returncode == 0 and "![After: home](" in dry.stdout, (dry.stdout, dry.stderr)
    real = run([PUBLISH, "T-1", "--repo", r, "--base", "main", "--web-base", WEB], cwd=tmp_path)
    assert real.returncode == 1 and "failed" in real.stderr, "a real run without an origin says so"


def test_token_lint_reads_arbitrary_utility_values(tmp_path):
    """Found by an independent review: `p-[13px]` in a component passed, and the projects that matter write sizes that way."""
    r = ui_repo(tmp_path)
    (r / "app").mkdir(exist_ok=True)
    (r / "app/Button.tsx").write_text('export const B = () => <button className="p-[13px] md:text-[15px] m-[16px] border-[1px]" />\n')
    done = lint(r, "--tokens", "design/tokens.json", "--paths", "app/**/*.tsx")
    assert done.returncode == 1 and "`p-[13px]`" in done.stdout and "`md:text-[15px]`" in done.stdout, (done.stdout, done.stderr)
    assert "m-[16px]" not in done.stdout and "border-[1px]" not in done.stdout, "a token value and a hairline are fine"
