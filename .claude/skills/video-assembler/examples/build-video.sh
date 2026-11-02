#!/usr/bin/env bash
# Reference minimal render pipeline script
set -euo pipefail

PROJECT_DIR="${1:-.}"

echo "[Step 1] Linting composition..."
(cd "$PROJECT_DIR/src" && hyperframes lint index.html)

echo "[Step 2] Rendering visual track..."
(cd "$PROJECT_DIR/src" && hyperframes render . \
  --fps 30 \
  --quality looks \
  --low-memory-mode \
  --output ../renders/visuals.mp4)

echo "[Step 3] Assembling audio and video streams..."
ffmpeg -y \
  -i "$PROJECT_DIR/renders/visuals.mp4" \
  -i "$PROJECT_DIR/audio/narration-full.wav" \
  -c:v copy \
  -c:a aac -b:a 192k \
  -shortest \
  "$PROJECT_DIR/renders/final.mp4"

echo "✅ Render complete: $PROJECT_DIR/renders/final.mp4"

