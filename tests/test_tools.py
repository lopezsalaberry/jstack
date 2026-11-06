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
