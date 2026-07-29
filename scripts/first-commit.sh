#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

node scripts/privacy-preflight.mjs
node scripts/repo-preflight.mjs

if [[ ! -d .git ]]; then
  git init -b main
fi

git config core.autocrlf false

if ! git config user.name >/dev/null || ! git config user.email >/dev/null; then
  echo "Git 사용자 정보가 없습니다. 다음 명령으로 설정한 뒤 다시 실행하십시오." >&2
  echo "  git config --global user.name \"Your Name\"" >&2
  echo "  git config --global user.email \"you@example.com\"" >&2
  exit 1
fi

git add .
if git diff --cached --quiet; then
  echo "커밋할 변경 사항이 없습니다."
else
  git commit -m "chore: prepare HandFont Studio v3.3.1 privacy-safe deployment"
fi

REMOTE_URL="${1:-}"
if [[ -n "$REMOTE_URL" ]]; then
  if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "$REMOTE_URL"
  else
    git remote add origin "$REMOTE_URL"
  fi
fi

if git remote get-url origin >/dev/null 2>&1; then
  git push -u origin main
else
  echo "로컬 최초 커밋을 만들었습니다. 원격 URL을 인수로 전달하면 Push까지 수행합니다."
fi
