#!/bin/bash
# update-readme.sh -- Auto-updates the dynamic section of README.md
# Triggered by post-commit hook on every branch

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
README="$REPO_ROOT/README.md"
PLAN="$REPO_ROOT/PLAN.md"

if [ ! -f "$README" ]; then
  exit 0
fi

# If README doesn't have AUTO-UPDATE markers, skip
if ! grep -q "AUTO-UPDATE:START" "$README" 2>/dev/null; then
  exit 0
fi

# Helper: trim whitespace and carriage returns from numbers
trim() {
  echo "$1" | tr -d '[:space:]'
}

# --- Gather data ---

BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
COMMIT_SHORT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
COMMIT_DATE=$(git log -1 --format="%ci" 2>/dev/null | cut -c1-16 || echo "")
TOTAL_COMMITS=$(trim "$(git rev-list --count HEAD 2>/dev/null || echo 0)")
BRANCH_COUNT=$(trim "$(git branch -a 2>/dev/null | grep -v HEAD | wc -l)")

# Recent commits (last 10)
RECENT_COMMITS=$(git log --oneline -10 2>/dev/null || echo "No commits yet")

# Progress from PLAN.md
DONE=0
TODO=0
if [ -f "$PLAN" ]; then
  DONE=$(grep -c '\- \[x\]' "$PLAN" 2>/dev/null || true)
  TODO=$(grep -c '\- \[ \]' "$PLAN" 2>/dev/null || true)
  DONE=$(trim "$DONE")
  TODO=$(trim "$TODO")
fi
DONE=${DONE:-0}
TODO=${TODO:-0}
TOTAL=$((DONE + TODO))
if [ "$TOTAL" -gt 0 ]; then
  PERCENT=$((DONE * 100 / TOTAL))
else
  PERCENT=0
fi

# Progress bar (20 chars wide)
FILLED=$((PERCENT / 5))
EMPTY=$((20 - FILLED))
BAR=""
i=0; while [ $i -lt $FILLED ]; do BAR="${BAR}#"; i=$((i+1)); done
i=0; EBAR=""; while [ $i -lt $EMPTY ]; do EBAR="${EBAR}-"; i=$((i+1)); done
PROGRESS_BAR="[${BAR}${EBAR}]"

# Phase status from PLAN.md
phase_status() {
  local phase_name="$1"
  if [ ! -f "$PLAN" ]; then
    echo "Planned"
    return
  fi

  local section
  section=$(sed -n "/## ${phase_name}/,/^## /p" "$PLAN" 2>/dev/null | head -n -1)
  if [ -z "$section" ]; then
    echo "Planned"
    return
  fi

  local done_count todo_count total_count
  done_count=$(echo "$section" | grep -c '\- \[x\]' 2>/dev/null || true)
  todo_count=$(echo "$section" | grep -c '\- \[ \]' 2>/dev/null || true)
  done_count=$(trim "$done_count")
  todo_count=$(trim "$todo_count")
  done_count=${done_count:-0}
  todo_count=${todo_count:-0}
  total_count=$((done_count + todo_count))

  if [ "$total_count" -eq 0 ]; then
    echo "Planned"
  elif [ "$done_count" -eq "$total_count" ]; then
    echo "Done"
  elif [ "$done_count" -gt 0 ]; then
    echo "In Progress ($done_count/$total_count)"
  else
    echo "Planned"
  fi
}

P11=$(phase_status "Phase 1.1")
P12=$(phase_status "Phase 1.2")
P13=$(phase_status "Phase 1.3")
P14=$(phase_status "Phase 1.4")
P15=$(phase_status "Phase 1.5")
P16=$(phase_status "Phase 1.6")

# File counts (Python + TypeScript)
SRC_FILES=0
TEST_FILES=0
if [ -d "$REPO_ROOT/src" ]; then
  SRC_FILES=$(trim "$(find "$REPO_ROOT/src" -type f \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' \) 2>/dev/null | wc -l)")
  TEST_FILES=$(trim "$(find "$REPO_ROOT/tests" -type f -name '*.py' 2>/dev/null | wc -l)")
fi
SRC_FILES=${SRC_FILES:-0}
TEST_FILES=${TEST_FILES:-0}

# SQL migration count
SQL_FILES=0
if [ -d "$REPO_ROOT/migrations" ]; then
  SQL_FILES=$(trim "$(find "$REPO_ROOT/migrations" -type f -name '*.sql' 2>/dev/null | wc -l)")
fi
SQL_FILES=${SQL_FILES:-0}

# dbt model count
DBT_MODELS=0
if [ -d "$REPO_ROOT/dbt/models" ]; then
  DBT_MODELS=$(trim "$(find "$REPO_ROOT/dbt/models" -type f -name '*.sql' 2>/dev/null | wc -l)")
fi
DBT_MODELS=${DBT_MODELS:-0}

# --- Build dynamic section ---

read -r -d '' DYNAMIC << ENDBLOCK || true
<!-- AUTO-UPDATE:START -->
<!-- This section is auto-updated by scripts/update-readme.sh on every commit -->

## Project Status

**Last updated**: ${COMMIT_DATE} (\`${COMMIT_SHORT}\` on \`${BRANCH}\`)

### Overall Progress

\`\`\`
${PROGRESS_BAR} ${PERCENT}% (${DONE}/${TOTAL} tasks)
\`\`\`

### Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1.1 | Foundation | ${P11} |
| 1.2 | Bronze Layer | ${P12} |
| 1.3 | Silver Layer | ${P13} |
| 1.4 | Gold Layer | ${P14} |
| 1.5 | Dashboard | ${P15} |
| 1.6 | Testing | ${P16} |

### Stats

| Metric | Value |
|--------|-------|
| Total commits | ${TOTAL_COMMITS} |
| Branches | ${BRANCH_COUNT} |
| Source files | ${SRC_FILES} |
| Test files | ${TEST_FILES} |
| SQL migrations | ${SQL_FILES} |
| dbt models | ${DBT_MODELS} |

### Recent Activity

\`\`\`
${RECENT_COMMITS}
\`\`\`

<!-- AUTO-UPDATE:END -->
ENDBLOCK

# --- Replace dynamic section in README ---

awk -v new_content="$DYNAMIC" '
  /<!-- AUTO-UPDATE:START -->/ { print new_content; skip=1; next }
  /<!-- AUTO-UPDATE:END -->/ { skip=0; next }
  !skip { print }
' "$README" > "${README}.tmp"

mv "${README}.tmp" "$README"

echo "[update-readme] README.md updated (${PERCENT}% progress, branch: ${BRANCH})"
