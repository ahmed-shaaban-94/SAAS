#!/bin/bash
# brain-session-end.sh — Captures session context into the Second Brain vault.
# Trigger: Stop hook (fires when Claude session ends)
# Output:
#   - docs/brain/sessions/YYYY-MM-DD-HH-MM.md  (local only, gitignored)
#   - docs/brain/session-log.csv               (shared, tracked in git, append-only)
#   - docs/brain/_INDEX.md                     (local only, regenerated from CSV)

set -euo pipefail

# Require bash 4+ for associative arrays
if (( BASH_VERSINFO[0] < 4 )); then
  exit 0
fi

# ── Resolve project root ──────────────────────────────────────────────
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || true)}"
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi
# Support both regular repos and worktrees
if [ ! -d "$PROJECT_DIR/.git" ] && [ ! -f "$PROJECT_DIR/.git" ]; then
  exit 0
fi
cd "$PROJECT_DIR"

BRAIN_DIR="docs/brain"
SESSION_DIR="$BRAIN_DIR/sessions"
LOG_FILE="$BRAIN_DIR/session-log.csv"

# Ensure directories exist
mkdir -p "$SESSION_DIR"

# ── Gather session data ───────────────────────────────────────────────
TIMESTAMP=$(date '+%Y-%m-%dT%H:%M')
FILENAME=$(date '+%Y-%m-%d-%H-%M')
BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
USER=$(git config user.name 2>/dev/null | tr ',' ' ' || echo "unknown")

# Files changed: uncommitted (working tree + staged) against HEAD
DIFF_FILES=$(git diff --name-only HEAD 2>/dev/null || true)

# Recent commits on this branch (last 4 hours, max 20)
RECENT_COMMITS=$(git log --oneline --since="4 hours ago" --max-count=20 2>/dev/null || true)

# Collect all files from commits too
ALL_FILES="$DIFF_FILES"
if [ -n "$RECENT_COMMITS" ]; then
  while IFS= read -r commit_line; do
    sha=$(echo "$commit_line" | awk '{print $1}')
    commit_files=$(git diff-tree --no-commit-id --name-only -r "$sha" 2>/dev/null || true)
    ALL_FILES=$(printf '%s\n%s' "$ALL_FILES" "$commit_files")
  done <<< "$RECENT_COMMITS"
fi

# Deduplicate and remove empty lines
ALL_FILES=$(echo "$ALL_FILES" | sort -u | grep -v '^$' || true)

# If nothing changed and no recent commits, skip
if [ -z "$ALL_FILES" ] && [ -z "$RECENT_COMMITS" ]; then
  exit 0
fi

# ── Detect layers and modules from file paths ─────────────────────────
declare -A SEEN_LAYERS
declare -A SEEN_MODULES

while IFS= read -r file; do
  [ -z "$file" ] && continue

  case "$file" in
    migrations/*|src/datapulse/bronze/*|src/datapulse/import_pipeline/*)
      SEEN_LAYERS[bronze]=1 ;;
  esac
  case "$file" in
    dbt/models/staging/*|dbt/models/bronze/*)
      SEEN_LAYERS[silver]=1 ;;
  esac
  case "$file" in
    dbt/models/marts/*|src/datapulse/analytics/*|src/datapulse/forecasting/*|src/datapulse/targets/*)
      SEEN_LAYERS[gold]=1 ;;
  esac
  case "$file" in
    src/datapulse/api/*)
      SEEN_LAYERS[api]=1 ;;
  esac
  case "$file" in
    frontend/*)
      SEEN_LAYERS[frontend]=1 ;;
  esac
  case "$file" in
    tests/*|frontend/e2e/*)
      SEEN_LAYERS[test]=1 ;;
  esac

  if [[ "$file" =~ ^src/datapulse/([^/]+)/ ]]; then
    mod="${BASH_REMATCH[1]}"
    [[ "$mod" != __* ]] && SEEN_MODULES[$mod]=1
  fi
  [[ "$file" =~ ^dbt/ ]]        && SEEN_MODULES[dbt]=1
  [[ "$file" =~ ^frontend/ ]]   && SEEN_MODULES[frontend]=1
  [[ "$file" =~ ^migrations/ ]] && SEEN_MODULES[migrations]=1
done <<< "$ALL_FILES"

# Build semicolon-delimited strings for CSV
LAYERS_CSV=$(echo "${!SEEN_LAYERS[@]}" | tr ' ' '\n' | sort | paste -sd';' || true)
MODULES_CSV=$(echo "${!SEEN_MODULES[@]}" | tr ' ' '\n' | sort | paste -sd';' || true)

# ── Write local session note (personal detail, gitignored) ────────────
SESSION_FILE="$SESSION_DIR/${FILENAME}.md"

FILE_COUNT=$(echo "$ALL_FILES" | wc -l | tr -d ' ')
if [ "$FILE_COUNT" -gt 50 ]; then
  FILES_SECTION=$(echo "$ALL_FILES" | head -50 | sed 's/^/- /')
  FILES_SECTION="${FILES_SECTION}
- ... and $((FILE_COUNT - 50)) more"
else
  FILES_SECTION=$(echo "$ALL_FILES" | sed 's/^/- /')
fi

if [ -n "$RECENT_COMMITS" ]; then
  COMMITS_SECTION=$(echo "$RECENT_COMMITS" | sed 's/^/- /')
else
  COMMITS_SECTION="_No commits in this session._"
fi

# Build layer/module wikilink sections
LAYER_DESCS=()
for layer in $(echo "${!SEEN_LAYERS[@]}" | tr ' ' '\n' | sort); do
  case "$layer" in
    bronze)   LAYER_DESCS+=("- [[bronze]] -- raw data ingestion changes") ;;
    silver)   LAYER_DESCS+=("- [[silver]] -- staging/cleaning changes") ;;
    gold)     LAYER_DESCS+=("- [[gold]] -- analytics/aggregation changes") ;;
    api)      LAYER_DESCS+=("- [[api]] -- route/service changes") ;;
    frontend) LAYER_DESCS+=("- [[frontend]] -- dashboard/UI changes") ;;
    test)     LAYER_DESCS+=("- [[test]] -- test additions/fixes") ;;
  esac
done

MODULE_LINKS=()
for mod in $(echo "${!SEEN_MODULES[@]}" | tr ' ' '\n' | sort); do
  MODULE_LINKS+=("- [[${mod}]]")
done

LAYERS_SECTION=$( [ ${#LAYER_DESCS[@]} -gt 0 ] && printf '%s\n' "${LAYER_DESCS[@]}" || echo "_No recognized layers._" )
MODULES_SECTION=$( [ ${#MODULE_LINKS[@]} -gt 0 ] && printf '%s\n' "${MODULE_LINKS[@]}" || echo "_No recognized modules._" )

cat > "$SESSION_FILE" << ENDNOTE
---
date: ${TIMESTAMP}
branch: ${BRANCH}
user: ${USER}
layers: [${LAYERS_CSV/;/,}]
modules: [${MODULES_CSV/;/,}]
---
# Session ${TIMESTAMP}

## Files Changed
${FILES_SECTION}

## Commits
${COMMITS_SECTION}

## Layers Touched
${LAYERS_SECTION}

## Modules Touched
${MODULES_SECTION}
ENDNOTE

# ── Append to shared CSV log (tracked in git) ─────────────────────────
# Create with headers if it doesn't exist
if [ ! -f "$LOG_FILE" ]; then
  echo "timestamp,branch,user,layers,modules" > "$LOG_FILE"
fi

# Append one line — append-only, no conflicts on merge
echo "${TIMESTAMP},${BRANCH},${USER},[${LAYERS_CSV}],[${MODULES_CSV}]" >> "$LOG_FILE"

# ── Regenerate local _INDEX.md from shared CSV log ────────────────────
INDEX_FILE="$BRAIN_DIR/_INDEX.md"
UPDATED=$(date '+%Y-%m-%dT%H:%M')

# Read last 5 data rows from CSV (skip header)
LAST5=$(tail -n +2 "$LOG_FILE" 2>/dev/null | tail -5 | tac || true)

if [ -z "$LAST5" ]; then
  SESSION_ENTRIES="_No sessions recorded yet._"
else
  SESSION_ENTRIES=""
  while IFS=',' read -r ts branch user layers modules; do
    SESSION_ENTRIES="${SESSION_ENTRIES}
### ${ts}
- **Branch**: \`${branch}\`
- **User**: ${user}
- **Layers**: ${layers}
- **Modules**: ${modules}
"
  done <<< "$LAST5"
fi

cat > "$INDEX_FILE" << ENDINDEX
---
generated: true
last_updated: ${UPDATED}
---
# DataPulse Second Brain — Context Index

> Auto-generated from \`docs/brain/session-log.csv\` (shared team log).
> Shows last 5 sessions across all team members and branches.

## Recent Sessions (last 5)
${SESSION_ENTRIES}
## Vault Structure

- \`session-log.csv\` -- Shared team log (tracked in git, append-only)
- \`sessions/\`       -- Local session detail notes (gitignored, personal)
- \`_INDEX.md\`       -- Local index regenerated from CSV (gitignored)
- \`layers/\`         -- Medallion layer notes (Phase 2)
- \`modules/\`        -- Per-module knowledge (Phase 2)
- \`decisions/\`      -- Session-level decision records
- \`roles/\`          -- Role-scoped briefings (Phase 2)
- \`incidents/\`      -- Post-incident analyses
ENDINDEX

# ── Stage the shared log for next commit ──────────────────────────────
git add "$LOG_FILE" 2>/dev/null || true

exit 0
