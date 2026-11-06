#!/usr/bin/env python3
"""Combine independent judges' JSON into one table and a pass/fail against a target.

  aggregate.py --run DIR [--target 7] JUDGE.json [JUDGE.json ...]

A criterion passes for a project only when EVERY judge scored it at or above the
target, so one lenient judge cannot carry a result. Exit 0 when the project named by
--project passes everywhere (or no --project is given), 1 otherwise, 2 on bad input.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CRITERIA = ["scope", "focus", "originality", "parallel", "quota", "proof", "crossreview",
            "portability", "tests", "docs", "adoption", "guardrails", "drift", "maturity"]


def extract_json(text: str) -> dict:
    """The judge's answer is one JSON object; tolerate prose or a code fence around it."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object found")
    return json.loads(text[start:end + 1])


def load_judge(path: Path, labels: list[str]) -> dict:
    data = extract_json(path.read_text())
    scores = data.get("scores", {})
    for label in labels:
        for c in CRITERIA:
            v = scores.get(label, {}).get(c)
            if not isinstance(v, int) or isinstance(v, bool) or not 1 <= v <= 10:
                raise ValueError(f"{path.name}: {label}.{c} must be an integer 1-10, got {v!r}")
    return data


def combine(judges: list[dict], mapping: dict, target: int) -> dict:
    result: dict = {}
    for label, info in mapping.items():
        rows = {}
        for c in CRITERIA:
            per = [j["scores"][label][c] for j in judges]
            rows[c] = {"scores": per, "min": min(per), "spread": max(per) - min(per), "pass": min(per) >= target}
        mins = [r["min"] for r in rows.values()]
        result[info["project"]] = {
            "label": label, "criteria": rows,
            "mean_of_min": round(sum(mins) / len(mins), 2),
            "failing": [c for c, r in rows.items() if not r["pass"]],
        }
    return result


def render(result: dict, judges: list[dict], target: int) -> str:
    names = sorted(result)
    out = ["| criterion | " + " | ".join(names) + " |", "|---|" + ":-:|" * len(names)]
    for c in CRITERIA:
        cells = []
        for n in names:
            r = result[n]["criteria"][c]
            cells.append("/".join(str(s) for s in r["scores"]) + ("" if r["pass"] else " <"))
        out.append(f"| {c} | " + " | ".join(cells) + " |")
    out.append("| **mean of per-criterion minimum** | " + " | ".join(f"**{result[n]['mean_of_min']}**" for n in names) + " |")
    out.append("")
    out.append(f"Judges: {', '.join(j.get('judge', '?') for j in judges)}. Cells show each judge's score; "
               f"`<` marks a criterion under {target} for at least one judge.")
    for n in names:
        if result[n]["failing"]:
            out.append(f"- {n} below {target}: {', '.join(result[n]['failing'])}")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--target", type=int, default=7)
    ap.add_argument("--project", help="project whose pass/fail sets the exit code (default: none)")
    ap.add_argument("judges", nargs="+", type=Path)
    args = ap.parse_args()
    try:
        mapping = json.loads((args.run / "private" / "mapping.json").read_text())
        judges = [load_judge(p, list(mapping)) for p in args.judges]
    except (OSError, ValueError) as error:
        print(f"aggregate: {error}", file=sys.stderr)
        sys.exit(2)
    result = combine(judges, mapping, args.target)
    (args.run / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(render(result, judges, args.target))
    if args.project:
        if args.project not in result:
            print(f"aggregate: unknown project {args.project}", file=sys.stderr)
            sys.exit(2)
        sys.exit(1 if result[args.project]["failing"] else 0)


if __name__ == "__main__":
    main()
