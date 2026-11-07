"""Behavior of the tools the skills ship. Each test runs the real script."""
import json
import os
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


def test_reviewer_models_defaults_to_auto_and_the_preference_syntax_parses(tmp_path):
    r = repo(tmp_path, "# P\n\n## jstack settings\nreviewer_models: provider-a:model-x, auto\n")
    assert run([SETTINGS, "--repo", r, "reviewer_models"], cwd=tmp_path).stdout.strip() == "provider-a:model-x, auto"
    other = tmp_path / "second"
    other.mkdir()
    plain = repo(other)
    assert run([SETTINGS, "--repo", plain, "reviewer_models"], cwd=tmp_path).stdout.strip() == "auto"


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
