#!/usr/bin/env python3
"""Prepare a blinded evaluation run of tstack, pstack and jstack at their latest published versions.

  prepare.py --out DIR [--seed N] [--source NAME=URL_OR_PATH[#subdir]]...

Clones each project fresh (never a local working copy), snapshots the files with
`git archive` (nothing from the clones is executed), shuffles the projects into
A/B/C, and writes mechanical facts next to each snapshot. The mapping from label
to project stays in DIR/private/, outside what the judges are given (DIR/judge/).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import subprocess
import sys
import tarfile
import io
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCES = {
    "tstack": {"url": "https://github.com/t3dotgg/tstack.git", "subdir": "", "extra": [], "exclude": []},
    "pstack": {"url": "https://github.com/cursor/plugins.git", "subdir": "pstack",
               "extra": [".github", "scripts", "harness/pstack"], "exclude": []},
    "jstack": {"url": "https://github.com/lopezsalaberry/jstack.git", "subdir": "", "extra": [],
               "exclude": ["evals"]},
}
HARNESS_TOKENS = ("delegate_task", "watch_pull_request", "AskUserQuestion", "request_user_input",
                  "spawn_agent", "ScheduleWakeup", "Monitor", "TaskCreate", "Task tool", "subagent")
MODEL_RE = re.compile(r"\b(gpt-[\w.\-]+|claude-[\w.\-]+|grok[\w.\-]*|gemini[\w.\-]*|opus[\w.\-]*|sonnet[\w.\-]*)")
PERSONAL_RE = re.compile(r"(/home/\w+|/Users/\w+|~/base\b)")
ENV_RE = re.compile(r"\$\{?([A-Z][A-Z0-9_]{3,})\}?")
TEST_RE = re.compile(r"(^|/)(test_[^/]+\.py|[^/]+_test\.(py|go|ts|js|sh)|[^/]+\.(test|spec)\.[jt]sx?|tests?/[^/]+)$")


def run(args: list[str], cwd: Path | None = None) -> str:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True).stdout


def clone(url: str, dest: Path) -> str:
    # Local paths are allowed so the harness can be tested without the network.
    run(["git", "clone", "-q", url, str(dest)])
    return run(["git", "rev-parse", "HEAD"], dest).strip()


def archive(clone_dir: Path, paths: list[str], dest: Path, strip: str = "", exclude: tuple[str, ...] = ()) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    data = subprocess.run(["git", "archive", "HEAD", "--", *paths], cwd=clone_dir, capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for member in tar.getmembers():
            name = member.name
            if strip and name.startswith(strip + "/"):
                name = name[len(strip) + 1:]
            if not name or any(name == e or name.startswith(e + "/") for e in exclude):
                continue
            if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                continue  # never materialise links from untrusted repos
            target = (dest / name).resolve()
            if dest.resolve() not in target.parents and target != dest.resolve():
                continue
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(member).read())  # type: ignore[union-attr]


def git_facts(clone_dir: Path, subdir: str) -> dict:
    scope = ["--", subdir] if subdir else []
    log = run(["git", "log", "--format=%H|%ad|%an|%s", "--date=short", *scope], clone_dir).splitlines()
    dates = [line.split("|")[1] for line in log]
    authors = {line.split("|")[2] for line in log}
    prs = {m.group(1) for line in log for m in re.finditer(r"\(#(\d+)\)|pull request #(\d+)", line) if m.group(1)}
    tags = run(["git", "tag", "--list"], clone_dir).split()
    return {"commits": len(log), "first_commit": min(dates) if dates else None,
            "last_commit": max(dates) if dates else None, "authors": len(authors),
            "commits_with_pr_number": len(prs), "tags": len(tags)}


def file_facts(root: Path) -> dict:
    files = [p for p in root.rglob("*") if p.is_file()]
    rel = {p: p.relative_to(root).as_posix() for p in files}
    text: dict[Path, str] = {}
    for p in files:
        try:
            text[p] = p.read_text()
        except (UnicodeDecodeError, OSError):
            pass
    skills = [p for p in files if p.name == "SKILL.md"]
    md = [p for p in text if p.suffix == ".md"]
    env: set[str] = set()
    harness = {t: 0 for t in HARNESS_TOKENS}
    models: set[str] = set()
    personal = 0
    for p, body in text.items():
        if p.suffix not in (".md", ".yaml", ".yml", ".sh", ".py", ""):
            continue
        if rel[p].startswith(("tests/", "docs/guide/")) or "/tests/" in rel[p]:
            continue
        env.update(ENV_RE.findall(body))
        for token in HARNESS_TOKENS:
            harness[token] += body.count(token)
        models.update(MODEL_RE.findall(body))
        personal += len(PERSONAL_RE.findall(body))
    workflows = [rel[p] for p in files if ".github/workflows/" in rel[p] or rel[p].startswith(".github/workflows/")]
    lower = {rel[p].lower() for p in files}
    return {
        "files": len(files),
        "lines_total": sum(b.count("\n") for b in text.values()),
        "skills": len(skills),
        "skill_lines_total": sum(text[p].count("\n") for p in skills if p in text),
        "largest_skill_lines": max([text[p].count("\n") for p in skills if p in text], default=0),
        "markdown_files": len(md),
        "executables_or_scripts": len([r for r in rel.values() if re.search(r"\.(py|sh|mjs|ts)$", r) or "/scripts/" in r]),
        "test_files": len([r for r in rel.values() if TEST_RE.search(r)]),
        "ci_workflows": workflows,
        "has_license": any(n.startswith("license") for n in lower),
        "has_changelog": any(n.startswith("changelog") for n in lower),
        "has_contributing": any(n.startswith("contributing") for n in lower),
        "has_security_policy": any(n.startswith("security") for n in lower),
        "has_version_file_or_manifest": any(n in lower for n in ("version", "plugin.json", "package.json")),
        "readme_lines": next((text[p].count("\n") for p in text if rel[p].lower() == "readme.md"), 0),
        "doc_files_under_docs": len([r for r in rel.values() if r.startswith("docs/")]),
        "env_vars_referenced": sorted(env),
        "harness_specific_token_counts": {k: v for k, v in harness.items() if v},
        "distinct_model_ids_in_skills": sorted(models),
        "personal_path_mentions": personal,
    }


def prepare(out: Path, seed: int, sources: dict) -> dict:
    if out.exists() and any(out.iterdir()):
        sys.exit(f"{out} is not empty")
    private, judge = out / "private", out / "judge"
    private.mkdir(parents=True)
    judge.mkdir()
    names = sorted(sources)
    labels = ["A", "B", "C"][: len(names)]
    random.Random(seed).shuffle(names)
    mapping: dict = {}
    for label, name in zip(labels, names):
        spec = sources[name]
        clone_dir = private / "clones" / name
        sha = clone(spec["url"], clone_dir)
        sub = spec["subdir"]
        dest = judge / label
        archive(clone_dir, [sub] if sub else ["."], dest, strip=sub, exclude=tuple(spec["exclude"]))
        for extra in spec["extra"]:
            try:
                archive(clone_dir, [extra], dest / "_repo_context" / extra, strip=extra)
            except subprocess.CalledProcessError:
                pass
        facts = {"label": label, "snapshot_note": "mechanical facts; the judge reads the files for the rest",
                 "git": git_facts(clone_dir, sub), "files": file_facts(dest)}
        (judge / f"{label}.evidence.json").write_text(json.dumps(facts, indent=2) + "\n")
        mapping[label] = {"project": name, "url": spec["url"], "subdir": sub, "sha": sha}
    shutil.copy(HERE / "rubric.md", judge / "RUBRIC.md")
    shutil.copy(HERE / "brief.md", judge / "BRIEF.md")
    (private / "mapping.json").write_text(json.dumps(mapping, indent=2) + "\n")
    return mapping


def parse_sources(overrides: list[str]) -> dict:
    sources = {k: dict(v) for k, v in SOURCES.items()}
    for item in overrides:
        name, _, rest = item.partition("=")
        url, _, sub = rest.partition("#")
        if name not in sources:
            sys.exit(f"unknown source {name}")
        sources[name]["url"] = url
        if sub != "":
            sources[name]["subdir"] = sub
    return sources


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--source", action="append", default=[], help="override: NAME=URL_OR_PATH[#subdir]")
    args = ap.parse_args()
    mapping = prepare(args.out, args.seed, parse_sources(args.source))
    print(json.dumps({k: {"sha": v["sha"][:7]} for k, v in mapping.items()}))
    print(f"judge directory: {args.out / 'judge'}")


if __name__ == "__main__":
    main()
