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

BODY_TEMPLATE=".github/pull_request_template.md"
TMP_BODY="$(mktemp)"
{
  echo "Auto-created PR for branch \`${BRANCH}\`."
  echo
  if [[ -f "${BODY_TEMPLATE}" ]]; then
    cat "${BODY_TEMPLATE}"
  else
    echo "Summary"
    echo
    echo "What does this change do?"
    echo
    echo "Checklist"
    echo "- [ ] Tests pass locally"
    echo "- [ ] No test can touch the dev DB (uses postgres_test only)"
    echo "- [ ] Any migrations included (if schema changes)"
    echo "- [ ] Docs updated (README / docs/)"
    echo "- [ ] No hardcoded secrets or account identifiers"
    echo
    echo "Risk / Rollback"
    echo "What could break? How do we roll back?"
    echo
  fi
} > "${TMP_BODY}"

gh pr create \
  --title "${TYPE}: ${TITLE}" \
  --draft \
  --body-file "${TMP_BODY}" \
  --head "${BRANCH}" \
  --base "main"

rm -f "${TMP_BODY}"


