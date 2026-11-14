"""jstack must describe only what it ships. These tests keep the docs and skills honest."""
import re
import subprocess
import sys
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
EXTRAS = sorted((ROOT / "extras").glob("*/SKILL.md"))
PROSE = [*SKILLS, *EXTRAS, *ROOT.glob("docs/*.md"), ROOT / "README.md", ROOT / "templates/AGENTS.md", ROOT / "AGENTS.md"]
_loader = SourceFileLoader("jstack_settings", str(ROOT / "skills/jstack/scripts/jstack-settings"))
settings = importlib.util.module_from_spec(importlib.util.spec_from_loader("jstack_settings", _loader))
_loader.exec_module(settings)

# Tool names that belong to one harness. They may appear only in the jstack skill's action table.
HARNESS_TOOLS = ("delegate_task", "watch_pull_request", "unwatch_pull_request", "AskUserQuestion",
                 "request_user_input", "spawn_agent", "t3_background_wait", "ScheduleWakeup",
                 "orchestrator_capabilities")
FIXED_MODEL = re.compile(r"\b(gpt-\d[\w.\-]*|claude-(opus|sonnet|haiku|fable)[\w.\-]*|gemini-\d[\w.\-]*)")
NOT_SETTINGS = {"started_at", "pr_wait", "wave_status"}  # snake_case words that are not setting keys


def test_the_linter_passes():
    out = subprocess.run([sys.executable, str(ROOT / "tools/lint.py")], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout


def test_every_script_a_skill_mentions_exists_and_is_executable():
    shipped = {p.name: p for d in ("skills", "extras") for p in ROOT.glob(f"{d}/*/scripts/*") if p.is_file()}
    for path in PROSE:
        for name in set(re.findall(r"scripts/([a-z][\w-]*)", path.read_text())):
            assert name in shipped, f"{path.relative_to(ROOT)} mentions scripts/{name}, which no skill ships"
            assert shipped[name].stat().st_mode & 0o111, f"{shipped[name]} is not executable"


def test_every_setting_a_skill_names_is_defined():
    known = set(settings.DEFAULTS) | set(HARNESS_TOOLS)  # the action table names tools
    for path in PROSE:
        for key in set(re.findall(r"`([a-z]+(?:_[a-z]+)+)`", path.read_text())) - NOT_SETTINGS:
            assert key in known, f"{path.relative_to(ROOT)} names `{key}`, which is not a jstack setting"


def test_every_setting_has_a_row_in_the_core_skill():
    core = (ROOT / "skills/jstack/SKILL.md").read_text()
    for key in settings.DEFAULTS:
        assert f"| `{key}` |" in core, f"setting {key} is undocumented in the jstack skill"


def test_harness_tools_and_fixed_models_stay_in_their_one_place():
    for path in PROSE:
        text = path.read_text()
        rel = path.relative_to(ROOT).as_posix()
        if rel != "skills/jstack/SKILL.md":
            for tool in HARNESS_TOOLS:
                assert tool not in text, f"{rel} names the harness tool {tool}; use an action from the jstack skill"
        assert not FIXED_MODEL.search(text), f"{rel} hardcodes a model id; use the models settings"


def test_inspiration_is_credited_in_the_readme_and_notice_only():
    readme = (ROOT / "README.md").read_text()
    assert "## Inspired by" in readme and "NOTICE" in readme
    for path in PROSE:
        if path.name == "README.md":
            continue
        assert not re.search(r"\b(tstack|pstack|rstack)\b", path.read_text(), re.I), path


def test_the_shipped_template_parses_with_the_shipped_reader(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "AGENTS.md").write_text((ROOT / "templates/AGENTS.md").read_text())
    values = settings.resolve(repo, env={})
    assert values["integration_branch"] == "main" and values["ui_paths"] == "" and values["design_tokens"] == "design/tokens.json"


def test_the_readme_lists_exactly_the_skills_that_ship():
    readme = (ROOT / "README.md").read_text()
    table = set(re.findall(r"^\| `([a-z][a-z0-9-]*)` \|", readme, re.M))
    shipped = {p.parent.name for p in SKILLS}
    assert table == shipped, f"README skill table out of sync: missing {sorted(shipped - table)}, extra {sorted(table - shipped)}"


def test_every_relative_link_in_the_docs_resolves():
    for path in [ROOT / "README.md", *ROOT.glob("docs/*.md"), ROOT / "CONTRIBUTING.md", ROOT / "SECURITY.md"]:
        for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", path.read_text()):
            if re.match(r"^[a-z]+:", target):
                continue
            assert (path.parent / target).exists(), f"{path.relative_to(ROOT)} links to {target}, which does not exist"
