#!/usr/bin/env python3
"""Repo linter: skill frontmatter, skill references."""
import re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
errors = []
skills = {p.parent.name: p for p in (ROOT / "skills").glob("*/SKILL.md")}
for name, p in skills.items():
    s = p.read_text()
    m = re.match(r"---\n(.*?)\n---\n", s, re.S)
    if not m: errors.append(f"{p}: missing frontmatter"); continue
    fm = dict(re.findall(r"^(\w[\w-]*):\s*(.*)$", m.group(1), re.M))
    if fm.get("name") != name: errors.append(f"{p}: name {fm.get('name')!r} != folder {name!r}")
    if not fm.get("description"): errors.append(f"{p}: missing description")
    if not re.search(r"^> (Source|Adapted|New in jstack)", s, re.M): errors.append(f"{p}: missing source line")
    refs = set(re.findall(r"\.\./([a-z0-9-]+)/SKILL\.md", s)) | set(re.findall(r"`([a-z0-9-]+)` skill", s))
    for ref in refs - set(skills):
        if not ref.startswith("verify"): errors.append(f"{p}: references missing skill {ref!r}")
for e in errors: print(e)
print(f"lint: {len(skills)} skills, {len(errors)} errors")
sys.exit(1 if errors else 0)
