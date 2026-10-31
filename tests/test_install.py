import os
from pathlib import Path
from conftest import sh, ROOT

def install(env, *args, check=True):
    return sh([str(ROOT / "install.sh"), *args], env=env, check=check)

def test_install_idempotent_backup_uninstall(env):
    home = Path(env["HOME"])
    old = home / ".claude/skills/sol-loop"; old.mkdir(parents=True); (old / "SKILL.md").write_text("old")
    hermes = str(home / ".hermes/skills")
    install(env, "--target", hermes)
    for d in (".claude/skills", ".agents/skills", ".hermes/skills"):
        assert os.readlink(home / d / "fanout") == str(ROOT / "skills/fanout")
    backup = list((home / ".claude/skills").glob(".jstack-backup-*/sol-loop/SKILL.md"))
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
