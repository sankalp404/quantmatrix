#!/usr/bin/env bash
set -euo pipefail

# Create a conventional commit PR for the current working tree.
#
# Requirements:
# - gh CLI installed and authenticated OR GH_TOKEN set with:
#   - contents:write
#   - pull_requests:write
#
# Usage:
#   scripts/open_pr.sh fix "prevent dev DB usage in tests"
#   scripts/open_pr.sh feat "add github actions CI"
#   scripts/open_pr.sh chore "infra cleanup"

TYPE="${1:-}"
TITLE="${2:-}"

if [[ -z "${TYPE}" || -z "${TITLE}" ]]; then
  echo "Usage: $0 <type: feat|fix|chore|docs|refactor|test> \"short title\""
  exit 2
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found. Install GitHub CLI or use a GitHub App/token flow."
  exit 2
fi

BRANCH="agent/${TYPE}/$(echo "${TITLE}" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//')-$(date +%Y%m%d)"

git status --porcelain >/dev/null

if [[ -n "$(git status --porcelain)" ]]; then
  git checkout -b "${BRANCH}"
  git add -A
  git commit -m "${TYPE}: ${TITLE}"
else
  echo "No changes to commit."
  exit 0
fi

git push -u origin "${BRANCH}"

gh pr create \
  --title "${TYPE}: ${TITLE}" \
  --body "Automated PR created by scripts/open_pr.sh" \
  --head "${BRANCH}" \
  --base "main"


