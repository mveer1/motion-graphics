#!/usr/bin/env bash
# ==============================================================================
# Motion Lab: Batch Portfolio Builder
# Sequentially builds and QA-verifies all projects under projects/
# Memory Rule: Strictly sequential execution for Apple Silicon (8 GB RAM).
#
# Usage: ./scripts/build-all.sh [--speed 1.15]
# ==============================================================================
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEED="${1:-}"

echo "================================================================="
echo "🏭  MOTION LAB BATCH PORTFOLIO BUILDER"
echo "================================================================="
echo "  • Base Directory: $BASE_DIR"
echo "  • Mode:           Strictly Sequential (Single Worker, Low-Memory)"
echo "================================================================="

PROJECT_DIRS=("$BASE_DIR"/projects/*)
TOTAL=${#PROJECT_DIRS[@]}
PASSED=0
FAILED=0
START_TIME=$(date +%s)

REPORT_ITEMS=()

for ((i=0; i<TOTAL; i++)); do
  P="${PROJECT_DIRS[$i]}"
  if [[ ! -d "$P" ]]; then continue; fi
  SLUG="$(basename "$P")"
  
  echo ""
  echo "-----------------------------------------------------------------"
  echo "[$((i+1))/$TOTAL] Building: $SLUG"
  echo "-----------------------------------------------------------------"

  CMD=("$BASE_DIR/scripts/build-project.sh" "$SLUG")
  if [[ -n "$SPEED" ]]; then
    CMD+=(--speed "$SPEED")
  fi

  P_START=$(date +%s)
  if "${CMD[@]}"; then
    P_END=$(date +%s)
    DUR=$((P_END - P_START))
    PASSED=$((PASSED + 1))
    
    OUT_FILE="$BASE_DIR/out/${SLUG}.mp4"
    SIZE="?"
    if [[ -f "$OUT_FILE" ]]; then
      SIZE="$(ls -lh "$OUT_FILE" | awk '{print $5}')"
    fi
    REPORT_ITEMS+=("✅ | $SLUG | ${DUR}s | $SIZE | PASS")
  else
    P_END=$(date +%s)
    DUR=$((P_END - P_START))
    FAILED=$((FAILED + 1))
    REPORT_ITEMS+=("❌ | $SLUG | ${DUR}s | - | FAIL")
  fi
done

TOTAL_END=$(date +%s)
TOTAL_ELAPSED=$((TOTAL_END - START_TIME))

echo ""
echo "================================================================="
echo "📊 BATCH PORTFOLIO BUILD REPORT"
echo "================================================================="
echo "  • Total Projects:  $TOTAL"
echo "  • Successful:      $PASSED"
echo "  • Failed:          $FAILED"
echo "  • Total Runtime:   ${TOTAL_ELAPSED}s"
echo "-----------------------------------------------------------------"
echo "Status | Project Slug | Build Time | File Size | QA Gate"
echo "-----------------------------------------------------------------"
for item in "${REPORT_ITEMS[@]}"; do
  echo "$item"
done
echo "================================================================="

exit $FAILED

