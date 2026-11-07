"""Tests of the tests: break the code on purpose and demand that the matching test notices.

A test that still passes when the behavior is wrong proves nothing. Each case copies the repo, makes
one small wrong change, and runs the one test that is supposed to guard it. That test must fail.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# (file, text to replace, wrong replacement, the test that must catch it)
MUTATIONS = {
    "an exhausted provider is reported as available": (
        "skills/quota-gate/scripts/quota-probe", "sys.exit(0 if max(mine) > 0 else 1)", "sys.exit(0)",
        "tests/test_tools.py::test_quota_probe_exit_codes_and_unknown_is_not_exhausted"),
    "a refusal mark is ignored": (
        "skills/quota-gate/scripts/quota-probe", "if args.provider and args.provider in live_marks(now):",
        "if False:",
        "tests/test_tools.py::test_a_refusal_marks_the_provider_and_every_later_worker_skips_it"),
    "the environment no longer overrides AGENTS.md": (
        "skills/jstack/scripts/jstack-settings", 'if f"JSTACK_{key.upper()}" in env:', "if False:",
        "tests/test_tools.py::test_settings_precedence_is_env_then_agents_md_then_default"),
    "a checklist that records no patch is accepted": (
        "skills/evidence/scripts/proof-valid", "if recorded in UNANCHORED and now != recorded:", "if False:",
        "tests/test_tools.py::test_a_checklist_started_before_the_change_is_never_called_valid"),
    "a stamp keeps the old patch id": (
        "skills/evidence/scripts/proof-valid", '("Patch-id", patch)', '("Patch-id", "empty")',
        "tests/test_tools.py::test_a_checklist_started_before_the_change_is_never_called_valid"),
    "a changed patch is still called valid": (
        "skills/evidence/scripts/proof-valid", "if recorded == now:", "if True:",
        "tests/test_tools.py::test_proof_follows_the_patch_not_the_commit"),
    "a rebase invalidates the proof": (
        "skills/evidence/scripts/proof-valid", 'fork = git("merge-base", base, ref).strip()',
        'fork = git("rev-parse", base).strip()',
        "tests/test_tools.py::test_proof_follows_the_patch_not_the_commit"),
    "the trail rewrites history": (
        "skills/jstack/scripts/trail", 'with path.open("a") as handle:', 'with path.open("w") as handle:',
        "tests/test_tools.py::test_trail_only_appends_and_neutralizes_formulas"),
    "a violation does not block": (
        "skills/full-send/scripts/token-lint", "    if found:\n        print(f\"token-lint: {found}", "    if False:\n        print(f\"token-lint: {found}",
        "tests/test_tools.py::test_token_lint_blocks_off_token_literals_and_suggests_the_nearest_color"),
    "committed changes are not looked at": (
        "skills/full-send/scripts/token-lint", 'fork = git("merge-base", base, "HEAD").strip()',
        'fork = git("rev-parse", "HEAD").strip()',
        "tests/test_tools.py::test_token_lint_blocks_off_token_literals_and_suggests_the_nearest_color"),
    "a bot that never reviews is still waited for": (
        "skills/babysit-pr/scripts/pr-wait", "if green and (reviewed or not GATING_BOTS):", "if green and reviewed:",
        "tests/test_tools.py::test_pr_wait_ready_does_not_wait_for_bots_that_are_not_configured"),
}


def copy_repo(dest: Path) -> Path:
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc"))
    return dest


def run_test(repo: Path, test_id: str):
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", test_id],
                          cwd=repo, capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_the_guarding_test_fails_when_the_behavior_is_broken(name, tmp_path):
    relative, old, new, test_id = MUTATIONS[name]
    clean = copy_repo(tmp_path / "clean")
    assert run_test(clean, test_id).returncode == 0, "the unmodified copy must pass first"
    broken = copy_repo(tmp_path / "broken")
    target = broken / relative
    source = target.read_text()
    assert old in source, f"the mutation no longer applies to {relative}: update this table"
    target.write_text(source.replace(old, new, 1))
    result = run_test(broken, test_id)
    assert result.returncode != 0, f"mutation '{name}' went unnoticed: {test_id} still passes"
