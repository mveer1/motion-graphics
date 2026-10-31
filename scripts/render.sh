#!/usr/bin/env bash
# ==============================================================================
# Motion Lab: Single-Command Project Renderer
# Usage: ./scripts/render.sh <project_dir>
# Example: ./scripts/render.sh benchmark-neural-network
# ==============================================================================
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_NAME="${1:-benchmark-neural-network}"

# Resolve project path in order: projects/<name>, <name>, or direct path
if [[ -d "$BASE_DIR/projects/$PROJECT_NAME" ]]; then
  PROJECT_DIR="$BASE_DIR/projects/$PROJECT_NAME"
elif [[ -d "$BASE_DIR/$PROJECT_NAME" ]]; then
  PROJECT_DIR="$BASE_DIR/$PROJECT_NAME"
elif [[ -d "$PROJECT_NAME" ]]; then
  PROJECT_DIR="$(cd "$PROJECT_NAME" && pwd)"
else
  echo "Error: Project directory '$PROJECT_NAME' not found in '$BASE_DIR/projects/' or '$BASE_DIR/'" >&2
  exit 1
fi

echo "=== Motion Lab Pipeline: $PROJECT_NAME ==="
mkdir -p "$PROJECT_DIR/renders"

# 1. Lint composition
echo "[1/4] Linting HyperFrames composition..."
(cd "$PROJECT_DIR/src" && hyperframes lint index.html)

# 2. Render visuals
echo "[2/4] Rendering visual track (HyperFrames)..."
(cd "$PROJECT_DIR/src" && hyperframes render . \
  --fps 30 \
  --quality looks \
  --low-memory-mode \
  --output ../renders/visuals.mp4 < /dev/null)

# 3. Assemble audio & video
echo "[3/4] Multiplexing video and audio with FFmpeg..."
AUDIO_FILE="$PROJECT_DIR/audio/narration-full.wav"
OUTPUT_FILE="$PROJECT_DIR/renders/final.mp4"

SFX_TRACK=""
if [[ -f "$PROJECT_DIR/audio/sfx-track.wav" ]]; then
  SFX_TRACK="$PROJECT_DIR/audio/sfx-track.wav"
elif [[ -f "$PROJECT_DIR/renders/film_sfx_sfx_track.wav" ]]; then
  SFX_TRACK="$PROJECT_DIR/renders/film_sfx_sfx_track.wav"
fi

BGM_TRACK=""
for bgm_candidate in "$PROJECT_DIR/audio/bgm.wav" "$PROJECT_DIR/audio/bgm.mp3" "$PROJECT_DIR/audio/music.mp3" "$PROJECT_DIR/audio/ambient.wav" "$PROJECT_DIR/audio/bed.wav"; do
  if [[ -f "$bgm_candidate" ]]; then
    BGM_TRACK="$bgm_candidate"
    break
  fi
done

if [[ -f "$AUDIO_FILE" ]] && [[ -n "$SFX_TRACK" ]] && [[ -n "$BGM_TRACK" ]]; then
  ffmpeg -y \
    -i "$PROJECT_DIR/renders/visuals.mp4" \
    -i "$AUDIO_FILE" \
    -i "$SFX_TRACK" \
    -i "$BGM_TRACK" \
    -filter_complex "[1:a]volume=1.0[a_voice];[2:a]volume=0.85[a_sfx];[3:a]volume=0.25[a_bgm];[a_voice][a_sfx][a_bgm]amix=inputs=3:duration=first:dropout_transition=2[aout]" \
    -map 0:v -map "[aout]" \
    -c:v copy \
    -c:a aac -b:a 192k \
    -shortest \
    "$OUTPUT_FILE" 2>/dev/null
  echo "✅ Assembled final video with narration, SFX, and background music: $OUTPUT_FILE"
elif [[ -f "$AUDIO_FILE" ]] && [[ -n "$SFX_TRACK" ]]; then
  ffmpeg -y \
    -i "$PROJECT_DIR/renders/visuals.mp4" \
    -i "$AUDIO_FILE" \
    -i "$SFX_TRACK" \
    -filter_complex "[1:a]volume=1.0[a_voice];[2:a]volume=0.85[a_sfx];[a_voice][a_sfx]amix=inputs=2:duration=first:dropout_transition=2[aout]" \
    -map 0:v -map "[aout]" \
    -c:v copy \
    -c:a aac -b:a 192k \
    -shortest \
    "$OUTPUT_FILE" 2>/dev/null
  echo "✅ Assembled final video with narration and SFX: $OUTPUT_FILE"
elif [[ -f "$AUDIO_FILE" ]] && [[ -n "$BGM_TRACK" ]]; then
  ffmpeg -y \
    -i "$PROJECT_DIR/renders/visuals.mp4" \
    -i "$AUDIO_FILE" \
    -i "$BGM_TRACK" \
    -filter_complex "[1:a]volume=1.0[a_voice];[2:a]volume=0.25[a_bgm];[a_voice][a_bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]" \
    -map 0:v -map "[aout]" \
    -c:v copy \
    -c:a aac -b:a 192k \
    -shortest \
    "$OUTPUT_FILE" 2>/dev/null
  echo "✅ Assembled final video with narration and background music: $OUTPUT_FILE"
elif [[ -f "$AUDIO_FILE" ]]; then
  ffmpeg -y \
    -i "$PROJECT_DIR/renders/visuals.mp4" \
    -i "$AUDIO_FILE" \
    -c:v copy \
    -c:a aac -b:a 192k \
    -shortest \
    "$OUTPUT_FILE" 2>/dev/null
  echo "✅ Assembled final video with narration: $OUTPUT_FILE"
else
  cp "$PROJECT_DIR/renders/visuals.mp4" "$OUTPUT_FILE"
  echo "⚠️ No narration track found. Outputting silent visuals: $OUTPUT_FILE"
fi

# 4. Probe verification
echo "[4/4] Verifying output integrity..."
ffprobe -v quiet -print_format json -show_streams "$OUTPUT_FILE" | python3.12 -c "
import json, sys
d = json.load(sys.stdin)
for s in d['streams']:
    print(f\"  • Stream {s['index']}: {s['codec_type']} ({s['codec_name']}) - duration {s.get('duration','?')}s\")
"
echo "=== Done! Output is ready at $OUTPUT_FILE ==="

# 5. Export to out/ for delivery
mkdir -p "$BASE_DIR/out"
cp "$OUTPUT_FILE" "$BASE_DIR/out/${PROJECT_NAME}.mp4"
echo "📦 Distribution delivery copy exported to: $BASE_DIR/out/${PROJECT_NAME}.mp4"

