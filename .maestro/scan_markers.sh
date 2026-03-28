#!/usr/bin/env bash
# scan_markers.sh — Scans the repository for TODO/FIXME/HACK/XXX/deprecated markers.
# Usage: bash .maestro/scan_markers.sh [repo_root]
# Output: Prints raw grep results (file:line:content) for all findings.

REPO="${1:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo /workspace)}"

PATTERN='TODO|FIXME|HACK|XXX|deprecated|DEPRECATED|@deprecated'

EXTENSIONS=(
  "*.py" "*.toml" "Makefile" "Dockerfile"
  "*.md" "*.sh" "*.cfg" "*.ini" "*.yml" "*.yaml"
)

INCLUDE_ARGS=()
for ext in "${EXTENSIONS[@]}"; do
  INCLUDE_ARGS+=(--include="$ext")
done

# Exclude the report output directory itself to avoid self-referential hits
grep -rn -E "$PATTERN" "${INCLUDE_ARGS[@]}" \
  --exclude-dir=".maestro/maintenance-reports" \
  "$REPO" 2>/dev/null
