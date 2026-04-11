#!/bin/bash
# brain-session-end.sh — Captures session context into the Second Brain vault.
# Trigger: Stop hook (fires when Claude session ends)
# Output: docs/brain/sessions/YYYY-MM-DD-HH-MM.md + regenerates docs/brain/_INDEX.md

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

# Ensure directories exist
mkdir -p "$SESSION_DIR"

# ── Gather session data ───────────────────────────────────────────────
TIMESTAMP=$(date '+%Y-%m-%dT%H:%M')
FILENAME=$(date '+%Y-%m-%d-%H-%M')
BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")

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

# If nothing changed and no recent commits, skip session note
if [ -z "$ALL_FILES" ] && [ -z "$RECENT_COMMITS" ]; then
  SKIP_NOTE=true
else
  SKIP_NOTE=false
fi

# ── Detect layers from file paths ────────────────────────────────────
declare -A SEEN_LAYERS
declare -A SEEN_MODULES

while IFS= read -r file; do
  [ -z "$file" ] && continue

  # Layer detection
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

  # Module detection: src/datapulse/<module>/
  if [[ "$file" =~ ^src/datapulse/([^/]+)/ ]]; then
    mod="${BASH_REMATCH[1]}"
    [[ "$mod" != __* ]] && SEEN_MODULES[$mod]=1
  fi
  # dbt as a module
  [[ "$file" =~ ^dbt/ ]] && SEEN_MODULES[dbt]=1
  # frontend as a module
  [[ "$file" =~ ^frontend/ ]] && SEEN_MODULES[frontend]=1
  # migrations as a module
  [[ "$file" =~ ^migrations/ ]] && SEEN_MODULES[migrations]=1
done <<< "$ALL_FILES"

# ── Build output sections ─────────────────────────────────────────────
# Layer descriptions for wikilinks
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

# YAML arrays
LAYERS_YAML=$(echo "${!SEEN_LAYERS[@]}" | tr ' ' '\n' | sort | paste -sd',' || true)
MODULES_YAML=$(echo "${!SEEN_MODULES[@]}" | tr ' ' '\n' | sort | paste -sd',' || true)

# Module wikilinks
MODULE_LINKS=()
for mod in $(echo "${!SEEN_MODULES[@]}" | tr ' ' '\n' | sort); do
  MODULE_LINKS+=("- [[${mod}]]")
done

# ── Write session note ────────────────────────────────────────────────
if [ "$SKIP_NOTE" = false ]; then
  SESSION_FILE="$SESSION_DIR/${FILENAME}.md"

  # Build files section (truncate at 50)
  FILE_COUNT=$(echo "$ALL_FILES" | wc -l | tr -d ' ')
  if [ "$FILE_COUNT" -gt 50 ]; then
    FILES_SECTION=$(echo "$ALL_FILES" | head -50 | sed 's/^/- /')
    FILES_SECTION="${FILES_SECTION}
- ... and $((FILE_COUNT - 50)) more"
  else
    FILES_SECTION=$(echo "$ALL_FILES" | sed 's/^/- /')
  fi

  # Build commits section
  if [ -n "$RECENT_COMMITS" ]; then
    COMMITS_SECTION=$(echo "$RECENT_COMMITS" | sed 's/^/- /')
  else
    COMMITS_SECTION="_No commits in this session._"
  fi

  # Build layers section
  if [ ${#LAYER_DESCS[@]} -gt 0 ]; then
    LAYERS_SECTION=$(printf '%s\n' "${LAYER_DESCS[@]}")
  else
    LAYERS_SECTION="_No recognized layers._"
  fi

  # Build modules section
  if [ ${#MODULE_LINKS[@]} -gt 0 ]; then
    MODULES_SECTION=$(printf '%s\n' "${MODULE_LINKS[@]}")
  else
    MODULES_SECTION="_No recognized modules._"
  fi

  cat > "$SESSION_FILE" << ENDNOTE
---
date: ${TIMESTAMP}
branch: ${BRANCH}
layers: [${LAYERS_YAML}]
modules: [${MODULES_YAML}]
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

fi

# ── Regenerate _INDEX.md ──────────────────────────────────────────────
INDEX_FILE="$BRAIN_DIR/_INDEX.md"

# Get last 5 session files (sorted by name = sorted by date)
SESSION_FILES=$(ls -1 "$SESSION_DIR"/*.md 2>/dev/null | sort -r | head -5 || true)

if [ -z "$SESSION_FILES" ]; then
  cat > "$INDEX_FILE" << 'ENDINDEX'
---
generated: true
last_updated: null
---
# DataPulse Second Brain — Context Index

> Auto-generated by `.claude/hooks/brain-session-end.sh`.
> Claude reads this at the start of every session for recent context.

## Recent Sessions

_No sessions recorded yet._
ENDINDEX
else
  UPDATED=$(date '+%Y-%m-%dT%H:%M')
  SESSION_ENTRIES=""

  while IFS= read -r sf; do
    [ -z "$sf" ] && continue
    # Extract frontmatter via grep (no yq dependency)
    S_DATE=$(grep '^date:' "$sf" 2>/dev/null | head -1 | sed 's/^date: *//' || echo "unknown")
    S_BRANCH=$(grep '^branch:' "$sf" 2>/dev/null | head -1 | sed 's/^branch: *//' || echo "unknown")
    S_LAYERS=$(grep '^layers:' "$sf" 2>/dev/null | head -1 | sed 's/^layers: *//' || echo "[]")
    S_MODULES=$(grep '^modules:' "$sf" 2>/dev/null | head -1 | sed 's/^modules: *//' || echo "[]")
    BASENAME=$(basename "$sf" .md)

    SESSION_ENTRIES="${SESSION_ENTRIES}
### [[sessions/${BASENAME}|${S_DATE}]]
- **Branch**: \`${S_BRANCH}\`
- **Layers**: ${S_LAYERS}
- **Modules**: ${S_MODULES}
"
  done <<< "$SESSION_FILES"

  cat > "$INDEX_FILE" << ENDINDEX
---
generated: true
last_updated: ${UPDATED}
---
# DataPulse Second Brain — Context Index

> Auto-generated by \`.claude/hooks/brain-session-end.sh\`.
> Claude reads this at the start of every session for recent context.

## Recent Sessions (last 5)
${SESSION_ENTRIES}
## Vault Structure

- \`sessions/\` -- Auto-generated session notes
- \`layers/\` -- Medallion layer notes (Phase 2)
- \`modules/\` -- Per-module knowledge from code graph (Phase 2)
- \`decisions/\` -- Lightweight decision records (Phase 2)
- \`roles/\` -- Role-scoped briefings (Phase 2)
- \`incidents/\` -- Post-incident analyses (Phase 2)
ENDINDEX
fi

# ── Done ──────────────────────────────────────────────────────────────
# Sessions and _INDEX.md are gitignored (local-only context).
# decisions/ and incidents/ are tracked and committed manually.
exit 0
