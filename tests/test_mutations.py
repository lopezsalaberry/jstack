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
        "skills/wave/scripts/quota-probe", "sys.exit(0 if max(mine) > 0 else 1)", "sys.exit(0)",
        "tests/test_tools.py::test_quota_probe_exit_codes_and_unknown_is_not_exhausted"),
    "a refusal mark is ignored": (
        "skills/wave/scripts/quota-probe", "if args.provider and args.provider in live_marks(now):", "if False:",
        "tests/test_tools.py::test_a_refusal_marks_the_provider_and_every_later_worker_skips_it"),
    "the shipped probe ignores the configured one": (
        "skills/wave/scripts/quota-probe", "        if command:\n            reading = ", "        if False:\n            reading = ",
        "tests/test_tools.py::test_the_shipped_probe_hands_the_call_to_the_configured_one"),
    "the shipped probe hands off again after a hand-off": (
        "skills/wave/scripts/quota-probe", 'if os.environ.get("JSTACK_QUOTA_HANDOFF"):', "if False:",
        "tests/test_tools.py::test_the_shipped_probe_hands_the_call_to_the_configured_one"),
    "a reset moment is replaced by an hour": (
        "skills/wave/scripts/quota-probe", "expires = parse_until(args.until, now)", "expires = now + 3600",
        "tests/test_tools.py::test_until_marks_a_provider_for_as_long_as_its_refusal_lasts"),
    "the environment no longer overrides AGENTS.md": (
        "skills/jstack/scripts/jstack-settings", 'if f"JSTACK_{key.upper()}" in env:', "if False:",
        "tests/test_tools.py::test_settings_precedence_is_env_then_agents_md_then_default"),
    "the operator's own settings are ignored": (
        "skills/jstack/scripts/jstack-settings", "        elif key in mine:", "        elif False:",
        "tests/test_tools.py::test_the_operators_own_settings_sit_between_the_repo_and_the_default"),
    "a checklist that records no patch is accepted": (
        "skills/ticket/scripts/proof-valid", "        if recorded in UNANCHORED:", "        if False:",
        "tests/test_tools.py::test_a_checklist_started_before_the_change_is_never_called_valid"),
    "a stamp keeps the old patch id": (
        "skills/ticket/scripts/proof-valid", '("Patch-id", patch)', '("Patch-id", "empty")',
        "tests/test_tools.py::test_a_checklist_started_before_the_change_is_never_called_valid"),
    "a changed patch is still called valid": (
        "skills/ticket/scripts/proof-valid", "if recorded == now:", "if True:",
        "tests/test_tools.py::test_proof_follows_the_patch_not_the_commit"),
    "a rebase invalidates the proof": (
        "skills/ticket/scripts/proof-valid", 'fork = git("merge-base", base, ref).strip()',
        'fork = git("rev-parse", base).strip()',
        "tests/test_tools.py::test_proof_follows_the_patch_not_the_commit"),
    "a violation does not block": (
        "skills/ticket/scripts/token-lint", "    if found:\n        print(f\"token-lint: {found}", "    if False:\n        print(f\"token-lint: {found}",
        "tests/test_tools.py::test_token_lint_blocks_off_token_literals_and_suggests_the_nearest_color"),
    "committed changes are not looked at": (
        "skills/ticket/scripts/token-lint", 'fork = git("merge-base", base, "HEAD").strip()',
        'fork = git("rev-parse", "HEAD").strip()',
        "tests/test_tools.py::test_token_lint_blocks_off_token_literals_and_suggests_the_nearest_color"),
    "test files are linted as UI": (
        "skills/ticket/scripts/token-lint", ',**/__tests__/**,**/*.test.*,**/*.spec.*"', '"',
        "tests/test_tools.py::test_token_lint_does_not_treat_test_files_as_ui"),
    "an edited card is called current": (
        "skills/jstack/scripts/doctor", '        if found and " ".join(found.group(0).split()) == " ".join(shipped.group(0).split()):',
        "        if found:",
        "tests/test_tools.py::test_doctor_says_when_no_file_an_agent_reads_has_the_current_card"),
    "the UI gate is silent when it is off": (
        "skills/jstack/scripts/doctor", "    if has_tokens:\n        return \"warn\"", "    if False:\n        return \"warn\"",
        "tests/test_tools.py::test_doctor_says_when_the_ui_gate_is_off"),
    "a checkout behind origin is called current": (
        "skills/jstack/scripts/doctor", "    if latest > mine:", "    if False:",
        "tests/test_tools.py::test_doctor_compares_the_checkout_with_the_newest_tag_when_asked"),
    "a later publish drops the earlier pictures": (
        "skills/ticket/scripts/publish", '            git(root, "read-tree", parent, env=env)', "            pass",
        "tests/test_tools.py::test_publish_builds_a_before_and_after_table_in_a_ref_nobody_fetches"),
    "the pictures go to a branch every worker fetches": (
        "skills/ticket/scripts/publish", 'f"refs/jstack-evidence/{args.ticket}"', 'f"refs/heads/jstack-evidence-{args.ticket}"',
        "tests/test_tools.py::test_publish_builds_a_before_and_after_table_in_a_ref_nobody_fetches"),
    "the whole folder is published": (
        "skills/ticket/scripts/publish", "        if len(files) > args.max_files or large:", "        if False:",
        "tests/test_tools.py::test_publish_refuses_the_folder_a_big_file_and_an_origin_nobody_can_open"),
    "a PASS that nobody ran passes the gate": (
        "skills/ticket/scripts/check", '        weak = [t for t, result, level in targets if result == "PASS" and level not in ("4", "5")]',
        "        weak = []",
        "tests/test_tools.py::test_check_passes_a_proven_change_and_names_what_is_missing"),
    "a change edited after its proof passes the gate": (
        "skills/ticket/scripts/check", "if valid.returncode != 0 else", "if False else",
        "tests/test_tools.py::test_check_fails_an_edited_change_an_off_token_color_and_a_branch_that_is_not_ready"),
    "work on the integration branch passes the gate": (
        "skills/ticket/scripts/check", 'say("FAIL" if branch in (target, "") else "PASS", "branch",', 'say("PASS", "branch",',
        "tests/test_tools.py::test_check_fails_an_edited_change_an_off_token_color_and_a_branch_that_is_not_ready"),
    "a status badge counts as a screenshot": (
        "skills/ticket/scripts/check", "for line in text.splitlines() if not NOT_A_SCREENSHOT.search(line)", "for line in text.splitlines() if True",
        "tests/test_tools.py::test_check_reads_the_pull_request_head_screenshot_review_ci_and_mergeability"),
    "a verdict on an older patch still counts": (
        "skills/ticket/scripts/check", 'run([sys.executable, str(HERE / "proof-valid"), "--patch-id", p, "--base", base], root).returncode == 1]',
        'False]',
        "tests/test_tools.py::test_check_reads_the_pull_request_head_screenshot_review_ci_and_mergeability"),
    "a failed CI check passes the gate": (
        "skills/ticket/scripts/check", "            if red:", "            if False:",
        "tests/test_tools.py::test_check_reads_the_pull_request_head_screenshot_review_ci_and_mergeability"),
    "a change with no UI file still needs a screenshot": (
        "skills/ticket/scripts/check", '            if not ui:\n                say("SKIP", "screenshot"', '            if False:\n                say("SKIP", "screenshot"',
        "tests/test_tools.py::test_check_asks_nothing_about_screens_of_a_change_with_no_ui_file"),
    "an unproven target passes the gate": (
        "skills/ticket/scripts/check", '        failed = [t for t, result, _ in targets if result != "PASS"]', "        failed = []",
        "tests/test_tools.py::test_check_passes_a_proven_change_and_names_what_is_missing"),
    "a verdict tied to no patch counts": (
        "skills/ticket/scripts/check", "            elif loose:", "            elif False:",
        "tests/test_tools.py::test_check_reads_the_pull_request_head_screenshot_review_ci_and_mergeability"),
    "a link that is not a picture counts as a screenshot": (
        "skills/ticket/scripts/check", 're.compile(rf"\\]\\(\\s*<?{FILE}", re.I),', 're.compile(r"\\]\\(\\s*<?https?://\\S+", re.I),',
        "tests/test_tools.py::test_check_reads_the_pull_request_head_screenshot_review_ci_and_mergeability"),
    "a branch with no change passes the gate": (
        "skills/ticket/scripts/check", 'say("PASS" if changed else "FAIL", "change",', 'say("PASS", "change",',
        "tests/test_tools.py::test_check_fails_an_edited_change_an_off_token_color_and_a_branch_that_is_not_ready"),
    "a mark for a mistyped year is accepted": (
        "skills/wave/scripts/quota-probe", "    if when > now + MAX_UNTIL_DAYS * 86400:", "    if False:",
        "tests/test_tools.py::test_until_marks_a_provider_for_as_long_as_its_refusal_lasts"),
    "an unreadable quota file reads as unknown": (
        "skills/wave/scripts/quota-probe", "            sys.exit(64)  # not 2", "            sys.exit(2)  # not 2",
        "tests/test_tools.py::test_quota_probe_rejects_a_malformed_line"),
    "an arbitrary utility size is not looked at": (
        "skills/ticket/scripts/token-lint", '        for m in UTILITY_LENGTH.finditer(text if lengths else ""):', '        for m in UTILITY_LENGTH.finditer(""):',
        "tests/test_tools.py::test_token_lint_reads_arbitrary_utility_values"),
    "a folder with no UI file gets the design block": (
        "skills/wave/scripts/brief", "        named += [f for f in tracked if f.startswith(folder) or pattern.match(f)]", "        named += tracked",
        "tests/test_tools.py::test_brief_adds_the_design_block_when_the_ticket_may_touch_ui"),
    "proof on a stand-in passes for the surface": (
        "skills/ticket/scripts/check", 'if result == "PASS" and level == "5" and where == surface.lower()]', 'if result == "PASS"]',
        "tests/test_tools.py::test_a_ticket_that_names_a_surface_is_not_done_until_it_is_proven_there"),
    "the required surface is never checked": (
        "skills/ticket/scripts/check", '        if surface.lower() not in ("", "none", "-"):', "        if False:",
        "tests/test_tools.py::test_a_ticket_that_names_a_surface_is_not_done_until_it_is_proven_there"),
    "a brief drops the surface": (
        "skills/wave/scripts/brief", "    if args.surface.strip():\n        lines.append(", "    if False:\n        lines.append(",
        "tests/test_tools.py::test_brief_asks_for_proof_on_the_surface_the_ticket_names"),
    "a brief is written without a model": (
        "skills/wave/scripts/brief", 'ap.add_argument(f"--{name}", required=True)', 'ap.add_argument(f"--{name}", default="x")',
        "tests/test_tools.py::test_brief_writes_a_brief_that_stands_alone_and_will_not_run_without_a_model"),
    "a UI brief has no design block": (
        "skills/wave/scripts/brief", "    if ui:\n        lines.append(", "    if False:\n        lines.append(",
        "tests/test_tools.py::test_brief_adds_the_design_block_when_the_ticket_may_touch_ui"),
    "a bot that never reviews is still waited for": (
        "skills/ticket/scripts/pr-wait", "if green and (reviewed or not GATING_BOTS):", "if green and reviewed:",
        "tests/test_tools.py::test_pr_wait_ready_does_not_wait_for_bots_that_are_not_configured"),
}


def copy_repo(dest: Path) -> Path:
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc", ".artifacts"))
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
