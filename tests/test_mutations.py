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
        "skills/evidence/scripts/proof-valid", "        if recorded in UNANCHORED:", "        if False:",
        "tests/test_tools.py::test_a_checklist_started_before_the_change_is_never_called_valid"),
    "a stamp keeps the old patch id": (
        "skills/evidence/scripts/proof-valid", '("Patch-id", patch)', '("Patch-id", "empty")',
        "tests/test_tools.py::test_a_checklist_started_before_the_change_is_never_called_valid"),
    "the shipped probe ignores the configured one": (
        "skills/quota-gate/scripts/quota-probe", "        if command:\n            os.execvpe", "        if False:\n            os.execvpe",
        "tests/test_tools.py::test_the_shipped_probe_hands_the_call_to_the_configured_one"),
    "the shipped probe hands off again after a hand-off": (
        "skills/quota-gate/scripts/quota-probe", 'if os.environ.get("JSTACK_QUOTA_HANDOFF"):', "if False:",
        "tests/test_tools.py::test_the_shipped_probe_hands_the_call_to_the_configured_one"),
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
    "an old copy of the template is called current": (
        "skills/jstack/scripts/template-drift", "    if mine < current:", "    if False:",
        "tests/test_tools.py::test_template_drift_names_old_copies"),
    "template versions are compared as text": (
        "skills/jstack/scripts/template-drift", "return tuple(int(x) for x in found.groups()) if found else None",
        "return tuple(found.groups()) if found else None",
        "tests/test_tools.py::test_template_drift_names_old_copies"),
    "the UI gate is silent when it is off": (
        "skills/jstack/scripts/doctor", "    if has_tokens:\n        return \"warn\"", "    if False:\n        return \"warn\"",
        "tests/test_tools.py::test_doctor_says_when_the_ui_gate_is_off"),
    "a checkout behind origin is called current": (
        "skills/jstack/scripts/doctor", "    if latest > mine:", "    if False:",
        "tests/test_tools.py::test_doctor_compares_the_checkout_with_the_newest_tag_when_asked"),
    "test files are linted as UI": (
        "skills/full-send/scripts/token-lint", ',**/__tests__/**,**/*.test.*,**/*.spec.*"', '"',
        "tests/test_tools.py::test_token_lint_does_not_treat_test_files_as_ui"),
    "the operator's own settings are ignored": (
        "skills/jstack/scripts/jstack-settings", "        elif key in mine:", "        elif False:",
        "tests/test_tools.py::test_the_operators_own_settings_sit_between_the_repo_and_the_default"),
    "a reset moment is replaced by an hour": (
        "skills/quota-gate/scripts/quota-probe", "expires = parse_until(args.until, now)", "expires = now + 3600",
        "tests/test_tools.py::test_until_marks_a_provider_for_as_long_as_its_refusal_lasts"),
    "a mark months away is accepted": (
        "skills/quota-gate/scripts/quota-probe", "    if when > now + MAX_UNTIL_DAYS * 86400:", "    if False:",
        "tests/test_tools.py::test_until_marks_a_provider_for_as_long_as_its_refusal_lasts"),
    "publishing a second ticket drops the first one's pictures": (
        "skills/evidence/scripts/publish", '            git(root, "read-tree", parent, env=env)', "            pass",
        "tests/test_tools.py::test_publish_shows_the_screenshots_from_a_ref_that_no_clone_downloads"),
    "the pictures go to a branch every clone fetches": (
        "skills/evidence/scripts/publish", 'f"refs/jstack-evidence/{args.ticket}", args.ticket, revision', 'f"refs/heads/jstack-evidence-{args.ticket}", args.ticket, revision',
        "tests/test_tools.py::test_publish_shows_the_screenshots_from_a_ref_that_no_clone_downloads"),
    "a whole folder is published": (
        "skills/evidence/scripts/publish", "        if len(files) > args.max_files:", "        if False:",
        "tests/test_tools.py::test_publish_shows_the_screenshots_from_a_ref_that_no_clone_downloads"),
    "a link that is not a picture counts as a screenshot": (
        "skills/evidence/scripts/pr-evidence-check", 're.compile(rf"\\]\\(\\s*<?{FILE}", re.I),', 're.compile(r"\\]\\(\\s*<?https?://\\S+", re.I),',
        "tests/test_tools.py::test_a_ui_change_needs_a_screenshot_the_reviewer_can_open"),
    "a later unproven patch is called landed": (
        "skills/evidence/scripts/proof-valid", "        if revision and now in UNANCHORED and subprocess.run(", "        if revision and recorded != now and subprocess.run(",
        "tests/test_tools.py::test_a_proof_is_not_called_landed_when_head_moved_on_to_another_patch"),
    "an unreadable quota file reads as unknown": (
        "skills/quota-gate/scripts/quota-probe", "            sys.exit(64)  # not 2", "            sys.exit(2)  # not 2",
        "tests/test_tools.py::test_quota_probe_rejects_a_malformed_line"),
    "an arbitrary utility size is not looked at": (
        "skills/full-send/scripts/token-lint", '        for m in UTILITY_LENGTH.finditer(text if lengths else ""):', '        for m in UTILITY_LENGTH.finditer(""):',
        "tests/test_tools.py::test_token_lint_reads_arbitrary_utility_values"),
    "a status badge counts as a screenshot": (
        "skills/evidence/scripts/pr-evidence-check", "        if NOT_EVIDENCE.search(line):", "        if False:",
        "tests/test_tools.py::test_a_ui_change_needs_a_screenshot_the_reviewer_can_open"),
    "a change with no UI file still needs a screenshot": (
        "skills/evidence/scripts/pr-evidence-check", "    if not ui_files:", "    if False:",
        "tests/test_tools.py::test_the_screenshot_check_only_applies_to_ui_changes_and_when_the_gate_is_on"),
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
