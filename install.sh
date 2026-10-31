#!/usr/bin/env bash
# install.sh: link jstack skills for every agent harness. Idempotent.
#
#   ./install.sh [--target DIR]... [--dry-run]
#   ./install.sh --uninstall [--target DIR]...
#
# Skill dirs: ~/.agents/skills and ~/.claude/skills, plus --target dirs.
# A same-name item that is not a jstack link is moved to
# <dir>/.jstack-backup-<timestamp>/ first.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
TS=$(date +%Y%m%d-%H%M%S)
TARGETS=("$HOME/.agents/skills" "$HOME/.claude/skills")
DRY=0; UNINSTALL=0
while [ $# -gt 0 ]; do
  case $1 in
    --target) [ $# -ge 2 ] || { echo "$1 needs a directory" >&2; exit 64; }; TARGETS+=("$2"); shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "unknown arg $1" >&2; exit 64 ;;
  esac
done
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
for dir in "${TARGETS[@]}"; do
  for src in "$ROOT"/skills/*/; do
    src=${src%/}; apply "$dir" "$(basename "$src")" "$src"
  done
done
echo "done. jstack $(cat "$ROOT/VERSION")"
