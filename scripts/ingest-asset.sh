#!/usr/bin/env bash
# ==============================================================================
# Ingest External Media Asset (Option A: Veo / Stock Footage / 3D Clips)
# Normalizes external video to project standards:
# - Resolution: 1280x720 (contain or crop to 16:9)
# - Frame rate: 30 fps constant
# - Audio: Stripped (silent video track)
# - Codec: H.264 High Profile (yuv420p)
# Usage: ./scripts/ingest-asset.sh <path_to_video> [asset_slug]
# ==============================================================================
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_PATH="${1:-}"

if [[ -z "$INPUT_PATH" || ! -f "$INPUT_PATH" ]]; then
  echo "Usage: ./scripts/ingest-asset.sh <path_to_raw_video.mp4> [asset_slug]" >&2
  exit 1
fi

FILENAME=$(basename -- "$INPUT_PATH")
SLUG="${2:-${FILENAME%.*}}"
OUTPUT_DIR="$BASE_DIR/assets/generated"
OUTPUT_FILE="$OUTPUT_DIR/${SLUG}-normalized.mp4"

mkdir -p "$OUTPUT_DIR"

echo "=== Normalizing External Asset: $FILENAME ==="
echo "Target: $OUTPUT_FILE (1280x720 @ 30fps, silent H.264)"

ffmpeg -y -i "$INPUT_PATH" \
  -vf "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=30" \
  -an \
  -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p \
  "$OUTPUT_FILE" 2>/dev/null

echo "✅ Normalized asset ready at: $OUTPUT_FILE"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,duration -of csv=p=0 "$OUTPUT_FILE" | head -1

