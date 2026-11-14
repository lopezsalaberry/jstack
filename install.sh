#!/usr/bin/env bash
# install.sh: link jstack skills for every agent harness. Idempotent.
#
#   ./install.sh [--target DIR]... [--extras] [--card FILE]... [--dry-run]
#   ./install.sh --uninstall [--target DIR]...
#   ./install.sh --doctor        check git, gh, python3, settings and links; installs nothing
#
# Skill dirs: ~/.agents/skills and ~/.claude/skills, plus --target dirs.
# --extras also links the skills in extras/ (PR watching for harnesses without a watcher,
#   takeover, PR comments, making a verify skill, turning mistakes into checks).
# --card FILE writes the rules card of templates/AGENTS.md into FILE, replacing the card
#   that is there or adding it at the end. FILE is a repo's AGENTS.md, or the file your
#   harness loads for every repo: one copy there serves every repo on the machine.
# A same-name item that is not a jstack link is moved to
# <dir>/.jstack-backup-<timestamp>/ first. A jstack link whose skill was renamed or
# removed is deleted.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
TS=$(date +%Y%m%d-%H%M%S)
TARGETS=("$HOME/.agents/skills" "$HOME/.claude/skills")
DRY=0; UNINSTALL=0; DOCTOR=0; EXTRAS=0; CARDS=()
while [ $# -gt 0 ]; do
  case $1 in
    --target) [ $# -ge 2 ] || { echo "$1 needs a directory" >&2; exit 64; }; TARGETS+=("$2"); shift 2 ;;
    --extras) EXTRAS=1; shift ;;
    --card) [ $# -ge 2 ] || { echo "$1 needs a file" >&2; exit 64; }; CARDS+=("$2"); shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    --doctor) DOCTOR=1; shift ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unknown arg $1" >&2; exit 64 ;;
  esac
done
if [ "$DOCTOR" = 1 ]; then exec python3 "$ROOT/skills/jstack/scripts/doctor"; fi
run() { if [ "$DRY" = 1 ]; then echo "+ $*"; else "$@"; fi; }
ours() { [ -L "$1" ] && [ "$(readlink "$1")" = "$2" ]; }
link() { # dir name src
  local dst=$1/$2
  if ours "$dst" "$3"; then return 0; fi
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    run mkdir -p "$1/.jstack-backup-$TS"
    run mv "$dst" "$1/.jstack-backup-$TS/$2"
    echo "backup: $dst -> $1/.jstack-backup-$TS/$2"
  fi
  run ln -s "$3" "$dst"; echo "linked: $dst"
}
apply() { # dir name src
  if [ "$UNINSTALL" = 1 ]; then
    if ours "$1/$2" "$3"; then run rm "$1/$2"; echo "removed: $1/$2"; fi
  else
    run mkdir -p "$1"; link "$1" "$2" "$3"
  fi
}
stale() { # dir: delete jstack links whose skill no longer exists
  local l t
  for l in "$1"/*; do
    [ -L "$l" ] || continue
    t=$(readlink "$l")
    case $t in "$ROOT"/skills/*|"$ROOT"/extras/*) [ -e "$t" ] || { run rm "$l"; echo "removed stale: $l"; } ;; esac
  done
}
for dir in "${TARGETS[@]}"; do
  [ "$UNINSTALL" = 1 ] || { [ -d "$dir" ] && stale "$dir"; }
  for src in "$ROOT"/skills/*/; do
    src=${src%/}; apply "$dir" "$(basename "$src")" "$src"
  done
  if [ "$EXTRAS" = 1 ] || [ "$UNINSTALL" = 1 ]; then
    for src in "$ROOT"/extras/*/; do
      src=${src%/}; apply "$dir" "$(basename "$src")" "$src"
    done
  fi
done
for file in ${CARDS[@]+"${CARDS[@]}"}; do
  python3 - "$ROOT/templates/AGENTS.md" "$file" "$DRY" <<'PY'
import re, sys
from pathlib import Path
card = re.compile(r"<!-- jstack-card -->.*?<!-- /jstack-card -->", re.S)
shipped = card.search(Path(sys.argv[1]).read_text()).group(0)
target, dry = Path(sys.argv[2]).expanduser(), sys.argv[3] == "1"
old = target.read_text() if target.is_file() else ""
new = card.sub(lambda _: shipped, old, count=1) if card.search(old) else (old.rstrip("\n") + "\n\n" if old.strip() else "") + shipped + "\n"
if new == old:
    print(f"card: {target} already has the current card")
elif dry:
    print(f"+ write the rules card into {target}")
else:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new)
    print(f"card: {'replaced in' if card.search(old) else 'added to'} {target}")
PY
done
echo "done. jstack $(cat "$ROOT/VERSION")"
