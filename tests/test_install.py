import os
from pathlib import Path
from conftest import sh, ROOT

def install(env, *args, check=True):
    return sh([str(ROOT / "install.sh"), *args], env=env, check=check)

def test_install_idempotent_backup_uninstall(env):
    home = Path(env["HOME"])
    old = home / ".claude/skills/cross-review"; old.mkdir(parents=True); (old / "SKILL.md").write_text("old")
    hermes = str(home / ".hermes/skills")
    install(env, "--target", hermes)
    for d in (".claude/skills", ".agents/skills", ".hermes/skills"):
        assert os.readlink(home / d / "fanout") == str(ROOT / "skills/fanout")
    backup = list((home / ".claude/skills").glob(".jstack-backup-*/cross-review/SKILL.md"))
    assert backup and backup[0].read_text() == "old"
    again = install(env, "--target", hermes)
    assert "linked:" not in again.stdout and "backup:" not in again.stdout
    install(env, "--uninstall", "--target", hermes)
    assert not (home / ".agents/skills/fanout").exists()
    assert not (home / ".hermes/skills/fanout").exists()
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
