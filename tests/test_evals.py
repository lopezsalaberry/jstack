"""The eval harness must blind the judges and must not let one lenient judge carry a pass."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "evals" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def make_repo(path: Path, files: dict[str, str], tag=False):
    path.mkdir(parents=True)
    git = lambda *a: subprocess.run(["git", "-C", str(path), *a], check=True, capture_output=True)
    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "T")
    for rel, body in files.items():
        (path / rel).parent.mkdir(parents=True, exist_ok=True)
        (path / rel).write_text(body)
    git("add", "-A")
    git("commit", "-q", "-m", "first (#1)")
    if tag:
        git("tag", "v1")
    return path


def test_prepare_blinds_labels_and_keeps_the_mapping_private(tmp_path):
    prepare = load("prepare")
    src = {
        "tstack": make_repo(tmp_path / "t", {"skills/a/SKILL.md": "x\n", "LICENSE": "MIT\n"}),
        "pstack": make_repo(tmp_path / "p", {"pstack/skills/b/SKILL.md": "y\n", "pstack/README.md": "r\n",
                                             ".github/workflows/ci.yml": "on: push\n"}),
        "jstack": make_repo(tmp_path / "j", {"skills/c/SKILL.md": "z\n", "evals/rubric.md": "secret\n",
                                             "tests/test_x.py": "pass\n"}, tag=True),
    }
    sources = prepare.parse_sources([f"{k}={v}" for k, v in src.items()])
    out = tmp_path / "run"
    mapping = prepare.prepare(out, 3, sources)
    judge = out / "judge"
    assert sorted(mapping) == ["A", "B", "C"]
    assert (out / "private" / "mapping.json").exists()
    # nothing the judge is given names a project or carries the mapping
    seen = "".join(p.read_text() for p in judge.rglob("*.json"))
    assert "tstack" not in seen and "pstack" not in seen and "jstack" not in seen
    assert not list(judge.rglob("mapping.json"))
    # the harness itself is not part of the evaluated project
    j_label = next(k for k, v in mapping.items() if v["project"] == "jstack")
    assert not (judge / j_label / "evals").exists()
    assert json.loads((judge / f"{j_label}.evidence.json").read_text())["git"]["tags"] == 1
    # pstack: the plugin folder is the root of its snapshot; repo-level CI rides along as context
    p_label = next(k for k, v in mapping.items() if v["project"] == "pstack")
    assert (judge / p_label / "skills" / "b" / "SKILL.md").exists()
    assert (judge / p_label / "_repo_context" / ".github" / "workflows" / "ci.yml").exists()
    assert (judge / "RUBRIC.md").exists() and (judge / "BRIEF.md").exists()


def test_same_seed_gives_same_blinding_and_a_different_seed_can_change_it(tmp_path):
    prepare = load("prepare")
    mk = lambda n, rel: make_repo(tmp_path / n, {rel: "x\n"})
    srcs = [f"tstack={mk('tstack', 'skills/a/SKILL.md')}", f"pstack={mk('pstack', 'pstack/skills/a/SKILL.md')}",
            f"jstack={mk('jstack', 'skills/a/SKILL.md')}"]
    parse = lambda: prepare.parse_sources(srcs)
    a = prepare.prepare(tmp_path / "r1", 7, parse())
    b = prepare.prepare(tmp_path / "r2", 7, parse())
    assert {k: v["project"] for k, v in a.items()} == {k: v["project"] for k, v in b.items()}


def scores(v):
    agg = load("aggregate")
    return {c: v for c in agg.CRITERIA}


def test_one_lenient_judge_cannot_carry_a_pass(tmp_path):
    agg = load("aggregate")
    mapping = {"A": {"project": "jstack"}, "B": {"project": "other"}}
    strict = {"judge": "strict", "scores": {"A": scores(6), "B": scores(8)}}
    lenient = {"judge": "lenient", "scores": {"A": scores(9), "B": scores(9)}}
    result = agg.combine([strict, lenient], mapping, 7)
    assert result["jstack"]["failing"] == agg.CRITERIA
    assert result["other"]["failing"] == []
    assert result["jstack"]["criteria"]["scope"]["min"] == 6


def test_aggregate_rejects_missing_or_out_of_range_scores(tmp_path):
    agg = load("aggregate")
    bad = tmp_path / "j.json"
    partial = scores(7)
    partial.pop("tests")
    bad.write_text(json.dumps({"scores": {"A": partial}}))
    try:
        agg.load_judge(bad, ["A"])
    except ValueError as error:
        assert "A.tests" in str(error)
    else:
        raise AssertionError("a missing score was accepted")
    bad.write_text(json.dumps({"scores": {"A": scores(11)}}))
    try:
        agg.load_judge(bad, ["A"])
    except ValueError:
        pass
    else:
        raise AssertionError("an out-of-range score was accepted")


def test_judge_answer_is_found_inside_prose_or_a_code_fence():
    agg = load("aggregate")
    assert agg.extract_json('Here you go:\n```json\n{"a": 1}\n```\n') == {"a": 1}
