#!/usr/bin/env bash
# ==============================================================================
# Motion Lab: Unified End-to-End Build Orchestrator
# Executes full lifecycle: Validate Research -> Build Audio -> Lint -> Render -> Mux -> QA
#
# Usage:
#   ./scripts/build-project.sh <project-slug> [--speed 1.15] [--rebuild-audio]
# Example:
#   ./scripts/build-project.sh benchmark-neural-network
# ==============================================================================
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -lt 1 ]]; then
  echo "Usage: ./scripts/build-project.sh <project-slug> [--speed <float>] [--rebuild-audio]"
  echo "Example: ./scripts/build-project.sh benchmark-neural-network --speed 1.15"
  exit 1
fi

PROJECT_ARG="$1"
shift

# Parse optional flags
SPEED=""
REBUILD_AUDIO=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --speed)
      SPEED="$2"
      shift 2
      ;;
    --rebuild-audio)
      REBUILD_AUDIO=true
      shift
      ;;
    *)
      echo "Unknown flag: $1" >&2
      shift
      ;;
  esac
done

# Resolve project path
if [[ -d "$BASE_DIR/projects/$PROJECT_ARG" ]]; then
  PROJECT_DIR="$BASE_DIR/projects/$PROJECT_ARG"
  SLUG="$PROJECT_ARG"
elif [[ -d "$BASE_DIR/$PROJECT_ARG" ]]; then
  PROJECT_DIR="$BASE_DIR/$PROJECT_ARG"
  SLUG="$(basename "$PROJECT_ARG")"
elif [[ -d "$PROJECT_ARG" ]]; then
  PROJECT_DIR="$(cd "$PROJECT_ARG" && pwd)"
  SLUG="$(basename "$PROJECT_DIR")"
else
  echo "Error: Project directory '$PROJECT_ARG' not found in projects/ or root." >&2
  exit 1
fi

# Multi-format studio projects (project.json) use the studio build: one render, mux and QA
# pass per delivery format. Legacy single-format explainers continue below unchanged.
if [[ -f "$PROJECT_DIR/project.json" ]]; then
  PY="${PYTHON_BIN:-}"
  if [[ -z "$PY" ]]; then
    for candidate in python3.12 python3 python; do
      if command -v "$candidate" >/dev/null 2>&1; then PY="$candidate"; break; fi
    done
  fi
  if [[ -n "$SPEED" || "$REBUILD_AUDIO" = true ]]; then
    echo "Note: --speed/--rebuild-audio apply to legacy projects; studio projects read voice and speed from project.json." >&2
  fi
  echo "project.json found: delegating to the multi-format studio build (scripts/studio.py build $SLUG)."
  exec "$PY" "$BASE_DIR/scripts/studio.py" build "$SLUG"
fi

echo "================================================================="
echo "🎬  MOTION LAB PRODUCTION ORCHESTRATOR"
echo "================================================================="
echo "  • Project:   $SLUG"
echo "  • Path:      $PROJECT_DIR"
if [[ -n "$SPEED" ]]; then
  echo "  • Speed:     ${SPEED}x override"
fi
echo "================================================================="

# ----------------------------------------------------------------------
# Stage 0: Research Dossier Validation
# ----------------------------------------------------------------------
if [[ -f "$PROJECT_DIR/research.json" ]]; then
  echo ""
  echo "[Stage 0] Validating technical research dossier against schema..."
  python3.12 "$BASE_DIR/scripts/validate-research.py" "$PROJECT_DIR/research.json"
else
  echo ""
  echo "⚠️  [Stage 0] No research.json found. Skipping schema validation gate."
fi

# ----------------------------------------------------------------------
# Stage 3: Audio Synthesis & Timeline Generation
# ----------------------------------------------------------------------
AUDIO_FULL="$PROJECT_DIR/audio/narration-full.wav"
if [[ "$REBUILD_AUDIO" = true ]] || [[ ! -f "$AUDIO_FULL" ]]; then
  echo ""
  echo "[Stage 3] Synthesizing voice clips and generating timeline map..."
  BUILD_AUDIO_CMD=(python3.12 "$BASE_DIR/scripts/build-audio.py" "$SLUG")
  if [[ -n "$SPEED" ]]; then
    BUILD_AUDIO_CMD+=(--speed "$SPEED")
  fi
  "${BUILD_AUDIO_CMD[@]}"
else
  echo ""
  echo "ℹ️  [Stage 3] Existing audio found at $AUDIO_FULL. (Use --rebuild-audio to force resynthesis)"
fi

# ----------------------------------------------------------------------
# Stage 5: Static Analysis & Composition Linting
# ----------------------------------------------------------------------
echo ""
echo "[Stage 5] Linting HyperFrames composition..."
(cd "$PROJECT_DIR/src" && hyperframes lint index.html)

# ----------------------------------------------------------------------
# Stage 6: Visual Track Render (Low-Memory Metal GPU)
# ----------------------------------------------------------------------
echo ""
echo "[Stage 6] Rendering visual track (Headless Chrome + Metal GPU)..."
mkdir -p "$PROJECT_DIR/renders"
(cd "$PROJECT_DIR/src" && hyperframes render . \
  --fps 30 \
  --quality looks \
  --low-memory-mode \
  --output ../renders/visuals.mp4)

# ----------------------------------------------------------------------
# Stage 8: Audio/Video Stream Multiplexing
# ----------------------------------------------------------------------
echo ""
echo "[Stage 8] Multiplexing video and audio with FFmpeg..."
FINAL_RENDER="$PROJECT_DIR/renders/final.mp4"

SFX_TRACK=""
if [[ -f "$PROJECT_DIR/audio/sfx-track.wav" ]]; then
  SFX_TRACK="$PROJECT_DIR/audio/sfx-track.wav"
elif [[ -f "$PROJECT_DIR/renders/film_sfx_sfx_track.wav" ]]; then
  SFX_TRACK="$PROJECT_DIR/renders/film_sfx_sfx_track.wav"
fi

if [[ -f "$AUDIO_FULL" ]] && [[ -n "$SFX_TRACK" ]]; then
  echo "  • Layering narration ($AUDIO_FULL) and sound effects ($SFX_TRACK)..."
  ffmpeg -y \
    -i "$PROJECT_DIR/renders/visuals.mp4" \
    -i "$AUDIO_FULL" \
    -i "$SFX_TRACK" \
    -filter_complex "[1:a]volume=1.0[a_voice];[2:a]volume=0.85[a_sfx];[a_voice][a_sfx]amix=inputs=2:duration=first:dropout_transition=2[aout]" \
    -map 0:v -map "[aout]" \
    -c:v copy \
    -c:a aac -b:a 192k \
    -shortest \
    "$FINAL_RENDER" 2>/dev/null
  echo "✅ Multiplexed master audio with SFX: $FINAL_RENDER"
elif [[ -f "$AUDIO_FULL" ]]; then
  ffmpeg -y \
    -i "$PROJECT_DIR/renders/visuals.mp4" \
    -i "$AUDIO_FULL" \
    -c:v copy \
    -c:a aac -b:a 192k \
    -shortest \
    "$FINAL_RENDER" 2>/dev/null
  echo "✅ Multiplexed master audio: $FINAL_RENDER"
else
  cp "$PROJECT_DIR/renders/visuals.mp4" "$FINAL_RENDER"
  echo "⚠️  Silent video produced (no narration track): $FINAL_RENDER"
fi

# ----------------------------------------------------------------------
# Stage 9: Automated Quality Assurance Gates
# ----------------------------------------------------------------------
echo ""
echo "[Stage 9] Executing automated QA gates (Loudness, Luminance, Codecs)..."
QA_SCRIPT="$BASE_DIR/.agents/skills/video-assembler/scripts/run-qa-gates.sh"
if [[ -x "$QA_SCRIPT" ]]; then
  "$QA_SCRIPT" "$FINAL_RENDER"
else
  # Fast fallback probe
  ffprobe -v quiet -print_format json -show_streams "$FINAL_RENDER" | python3.12 -c "
import json, sys
d = json.load(sys.stdin)
for s in d.get('streams', []):
    print(f\"  • Stream #{s['index']}: {s['codec_type']} ({s['codec_name']}), duration: {s.get('duration','?')}s\")
"
fi

# ----------------------------------------------------------------------
# Delivery Export
# ----------------------------------------------------------------------
mkdir -p "$BASE_DIR/out"
DELIVERY_FILE="$BASE_DIR/out/${SLUG}.mp4"
cp "$FINAL_RENDER" "$DELIVERY_FILE"

echo ""
echo "================================================================="
echo "🎉 PRODUCTION PIPELINE COMPLETE: $SLUG"
echo "================================================================="
echo "  • Working Render:   $FINAL_RENDER"
echo "  • Delivery Export:  $DELIVERY_FILE"
echo "================================================================="

