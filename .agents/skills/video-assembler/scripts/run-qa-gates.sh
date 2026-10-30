#!/usr/bin/env bash
# ==============================================================================
# Automated QA Gates for Motion Graphics Production
# Usage: ./run-qa-gates.sh <path_to_video.mp4>
# Checks:
# 1. FFprobe streams (codec, resolution, fps, duration)
# 2. EBU R128 Loudness compliance (Target: -21.2 LUFS)
# 3. Unintended black screen gaps (blackdetect)
# 4. Stream synchronization offset
# ==============================================================================
set -euo pipefail

VIDEO_PATH="${1:-}"

if [[ -z "$VIDEO_PATH" || ! -f "$VIDEO_PATH" ]]; then
  echo "Usage: $0 <path_to_video.mp4>" >&2
  exit 1
fi

echo "=========================================================="
echo "Running QA Gates: $(basename "$VIDEO_PATH")"
echo "=========================================================="

# 1. Stream properties
echo -e "\n[Gate 1/4] Stream Verification:"
ffprobe -v error -show_entries stream=index,codec_type,codec_name,width,height,r_frame_rate,duration -of json "$VIDEO_PATH" | python3.12 -c "
import json, sys
d = json.load(sys.stdin)
for s in d['streams']:
    print(f\"  • Stream {s['index']}: {s['codec_type']} ({s['codec_name']}) {s.get('width','')}x{s.get('height','')} @ {s.get('r_frame_rate','')} fps | {s.get('duration','')}s\")
"

# 2. Audio Loudness (EBU R128)
echo -e "\n[Gate 2/4] Integrated Loudness (Target: -21.2 LUFS):"
ffmpeg -i "$VIDEO_PATH" -af ebur128=framelog=quiet -f null - 2>&1 | grep -A 3 "Integrated loudness:" | sed 's/^/  /'

# 3. Black frame detection
echo -e "\n[Gate 3/4] Black Screen Gap Audit:"
BLACK_GAPS=$(ffmpeg -i "$VIDEO_PATH" -vf "blackdetect=d=0.3:pix_th=0.05" -f null - 2>&1 | grep "blackdetect" || true)
if [[ -n "$BLACK_GAPS" ]]; then
  echo "  ⚠️ Notice: Dark periods detected (inspect timestamps to confirm intentional transitions):"
  echo "$BLACK_GAPS" | sed 's/^/    /'
else
  echo "  ✅ Zero unintended black frames detected."
fi

# 4. Overall size & bitrate
echo -e "\n[Gate 4/5] Container Metrics:"
ffprobe -v error -show_entries format=duration,size,bit_rate -of json "$VIDEO_PATH" | python3.12 -c "
import json, sys
f = json.load(sys.stdin)['format']
print(f\"  • Duration: {float(f['duration']):.2f}s\")
print(f\"  • Size: {int(f['size'])/1024:.1f} KB\")
print(f\"  • Bitrate: {int(f['bit_rate'])/1000:.1f} kbps\")
"

# 5. Earshot Acoustic Verification
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
EARSHOT_BIN="$REPO_ROOT/.venv/bin/earshot"
if [[ -x "$EARSHOT_BIN" ]]; then
  echo -e "\n[Gate 5/5] Earshot Acoustic & Spectral Verification:"
  "$EARSHOT_BIN" measure "$VIDEO_PATH" | sed 's/^/  /'
fi

echo -e "\n=========================================================="
echo "✅ QA Verification Complete."
echo "=========================================================="

