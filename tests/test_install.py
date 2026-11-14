import os
from pathlib import Path
from conftest import sh, ROOT

def install(env, *args, check=True):
    return sh([str(ROOT / "install.sh"), *args], env=env, check=check)

def test_install_idempotent_backup_uninstall(env):
    home = Path(env["HOME"])
    old = home / ".claude/skills/review"; old.mkdir(parents=True); (old / "SKILL.md").write_text("old")
    hermes = str(home / ".hermes/skills")
    install(env, "--target", hermes)
    for d in (".claude/skills", ".agents/skills", ".hermes/skills"):
        assert os.readlink(home / d / "wave") == str(ROOT / "skills/wave")
    backup = list((home / ".claude/skills").glob(".jstack-backup-*/review/SKILL.md"))
    assert backup and backup[0].read_text() == "old"
    again = install(env, "--target", hermes)
    assert "linked:" not in again.stdout and "backup:" not in again.stdout
    install(env, "--uninstall", "--target", hermes)
    assert not (home / ".agents/skills/wave").exists()
    assert not (home / ".hermes/skills/wave").exists()
    assert backup[0].read_text() == "old"

def test_dry_run_changes_nothing(env):
    install(env, "--dry-run")
    assert not (Path(env["HOME"]) / ".claude").exists()

def test_bad_args(env):
    assert install(env, "--target", check=False).returncode == 64
    assert install(env, "--nope", check=False).returncode == 64


def test_install_removes_links_to_skills_that_no_longer_exist(env):
    home = Path(env["HOME"])
    skills = home / ".claude/skills"; skills.mkdir(parents=True)
    (skills / "gone").symlink_to(ROOT / "skills/gone")          # a renamed or removed jstack skill
    (skills / "foreign").symlink_to(home / "elsewhere")         # someone else's dangling link stays
    out = install(env)
    assert "removed stale" in out.stdout
    assert not (skills / "gone").is_symlink() and (skills / "foreign").is_symlink()


def test_doctor_flag_installs_nothing(env):
    out = install(env, "--doctor", check=False)
    assert "python3" in out.stdout and "git" in out.stdout
    assert not (Path(env["HOME"]) / ".claude").exists()


def test_extras_are_linked_only_when_asked_and_always_removed_on_uninstall(env):
    home = Path(env["HOME"])
    install(env)
    assert sorted(p.name for p in (home / ".claude/skills").iterdir()) == ["groom", "jstack", "review", "ticket", "wave"]
    install(env, "--extras")
    assert os.readlink(home / ".claude/skills/babysit-pr") == str(ROOT / "extras/babysit-pr")
    install(env, "--uninstall")
    assert list((home / ".claude/skills").iterdir()) == []


def test_card_is_written_once_replaced_in_place_and_never_duplicated(env):
    """One copy of the rules in a file the harness always loads serves every repo on the machine."""
    home = Path(env["HOME"])
    card = (ROOT / "templates/AGENTS.md").read_text().split("## jstack settings")[0].strip()
    target = home / ".claude" / "CLAUDE.md"
    target.parent.mkdir()
    target.write_text("# My notes\n\nkeep me\n")
    assert "added to" in install(env, "--card", str(target)).stdout
    assert target.read_text() == "# My notes\n\nkeep me\n\n" + card + "\n"
    assert "already has the current card" in install(env, "--card", str(target)).stdout
    edited = target.read_text().replace("**One gate.**", "**One gate, usually.**") + "\n## After\n"
    target.write_text(edited)
    assert "replaced in" in install(env, "--card", str(target)).stdout
    text = target.read_text()
    assert text.count("<!-- jstack-card -->") == 1 and "usually" not in text and text.endswith("\n## After\n") and "keep me" in text
    fresh = home / "repo" / "AGENTS.md"
    install(env, "--card", str(fresh))
    assert fresh.read_text() == card + "\n"
    before = fresh.read_text()
    assert "+ write the rules card" in install(env, "--dry-run", "--card", str(home / "none.md")).stdout and not (home / "none.md").exists()
    assert fresh.read_text() == before
    assert install(env, "--card", check=False).returncode == 64
