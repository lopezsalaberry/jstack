import os, subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent

def sh(cmd, env=None, check=True):
    e = dict(os.environ); e.update(env or {})
    r = subprocess.run(cmd, env=e, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise AssertionError(f"{cmd} -> {r.returncode}\n{r.stdout}\n{r.stderr}")
    return r

@pytest.fixture
def env(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    return {"HOME": str(home)}
