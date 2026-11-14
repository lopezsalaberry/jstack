#!/usr/bin/env python3
"""Repo linter: skill frontmatter, references between skills, and self-containment.

Self-containment means skills, docs, templates and tools describe only what this repo ships.
Credit to the projects that inspired jstack lives in README.md and NOTICE only.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CREDIT_ONLY = {"README.md", "NOTICE", "LICENSE"}
# Other projects and their authors: never named in how jstack works.
OTHER_PROJECTS = re.compile(r"\b(tstack|pstack|rstack|t3dotgg|backnotprop|michaelshimeles|poteto|cursor/plugins)\b", re.I)
errors = []

skills = {p.parent.name: p for d in ("skills", "extras") for p in (ROOT / d).glob("*/SKILL.md")}
for name, p in skills.items():
    s = p.read_text()
    m = re.match(r"---\n(.*?)\n---\n", s, re.S)
    if not m:
        errors.append(f"{p}: missing frontmatter")
        continue
    fm = dict(re.findall(r"^(\w[\w-]*):\s*(.*)$", m.group(1), re.M))
    if fm.get("name") != name:
        errors.append(f"{p}: name {fm.get('name')!r} != folder {name!r}")
    if not fm.get("description"):
        errors.append(f"{p}: missing description")
    refs = set(re.findall(r"\.\./([a-z0-9-]+)/SKILL\.md", s)) | set(re.findall(r"`([a-z0-9-]+)` skill", s))
    for ref in refs - set(skills):
        if not ref.startswith("verify"):
            errors.append(f"{p}: references a skill this repo does not ship: {ref!r}")

SCOPE = [*ROOT.glob("skills/**/*"), *ROOT.glob("extras/**/*"), *ROOT.glob("docs/**/*"), *ROOT.glob("templates/**/*"),
         *ROOT.glob("tools/**/*"), ROOT / "AGENTS.md", ROOT / "install.sh", ROOT / "Makefile"]
for path in sorted(set(SCOPE)):
    if not path.is_file() or path.name in CREDIT_ONLY or "__pycache__" in path.parts or path == Path(__file__).resolve():
        continue
    try:
        text = path.read_text()
    except UnicodeDecodeError:
        continue
    for n, line in enumerate(text.splitlines(), 1):
        if OTHER_PROJECTS.search(line):
            errors.append(f"{path.relative_to(ROOT)}:{n}: names another project; credit belongs in README.md or NOTICE")

for e in errors:
    print(e)
print(f"lint: {len(skills)} skills, {len(errors)} errors")
sys.exit(1 if errors else 0)
