#!/usr/bin/env bash
# ==============================================================================
# Automated QA Gates for Motion Graphics Production
# Usage:
#   run-qa-gates.sh <video.mp4> [--expect-width N] [--expect-height N] [--expect-fps N]
#                   [--expect-duration SEC] [--duration-tolerance SEC]
#                   [--expect-lufs LUFS] [--lufs-tolerance LU] [--allow-silent]
# Gates:
#   1. Stream verification (codec, resolution, fps, duration)
#   2. EBU R128 integrated loudness
#   3. Unintended black screen gaps (blackdetect; advisory)
#   4. Container metrics (duration, size, bitrate)
#   5. Earshot acoustic verification (when .venv/bin/earshot exists and audio is present)
# Without --expect-* flags every gate is informational (legacy behaviour). With them, a
# mismatch is a failure and the script exits 2. scripts/studio.py build passes the
# expectations for each delivery format. PYTHON_BIN overrides the Python interpreter.
# ==============================================================================
set -euo pipefail
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

usage() {
  cat >&2 <<'EOF'
Usage: run-qa-gates.sh <video.mp4> [--expect-width N] [--expect-height N] [--expect-fps N]
                       [--expect-duration SEC] [--duration-tolerance SEC]
                       [--expect-lufs LUFS] [--lufs-tolerance LU] [--allow-silent]
EOF
}

VIDEO_PATH="${1:-}"
if [[ -z "$VIDEO_PATH" || "$VIDEO_PATH" == -* ]]; then
  usage
  exit 1
fi
shift

EXPECT_WIDTH=""
EXPECT_HEIGHT=""
EXPECT_FPS=""
EXPECT_DURATION=""
DURATION_TOL="0.15"
EXPECT_LUFS=""
LUFS_TOL="2"
ALLOW_SILENT=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --expect-width) EXPECT_WIDTH="${2:?--expect-width needs a value}"; shift 2 ;;
    --expect-height) EXPECT_HEIGHT="${2:?--expect-height needs a value}"; shift 2 ;;
    --expect-fps) EXPECT_FPS="${2:?--expect-fps needs a value}"; shift 2 ;;
    --expect-duration) EXPECT_DURATION="${2:?--expect-duration needs a value}"; shift 2 ;;
    --duration-tolerance) DURATION_TOL="${2:?--duration-tolerance needs a value}"; shift 2 ;;
    --expect-lufs) EXPECT_LUFS="${2:?--expect-lufs needs a value}"; shift 2 ;;
    --lufs-tolerance) LUFS_TOL="${2:?--lufs-tolerance needs a value}"; shift 2 ;;
    --allow-silent) ALLOW_SILENT=true; shift ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ ! -f "$VIDEO_PATH" ]]; then
  echo "Error: video not found: $VIDEO_PATH" >&2
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  for candidate in python3.12 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
fi
if [[ -z "$PYTHON_BIN" ]]; then
  echo "Error: no Python interpreter found (set PYTHON_BIN)." >&2
  exit 1
fi

STRICT=false
if [[ -n "$EXPECT_WIDTH$EXPECT_HEIGHT$EXPECT_FPS$EXPECT_DURATION$EXPECT_LUFS" ]]; then
  STRICT=true
fi
FAILURES=0
fail() {
  echo "  ❌ $1"
  FAILURES=$((FAILURES + 1))
}
problem() {
  if [[ "$STRICT" == true ]]; then fail "$1"; else echo "  ⚠️ $1"; fi
}

echo "=========================================================="
echo "Running QA Gates: $(basename "$VIDEO_PATH")"
echo "=========================================================="

# 1. Stream properties
echo -e "\n[Gate 1/5] Stream Verification:"
PROBE_JSON="$(ffprobe -v error -show_entries stream=index,codec_type,codec_name,width,height,r_frame_rate,duration:format=duration -of json "$VIDEO_PATH")"
GATE1_OUT="$(PROBE_JSON="$PROBE_JSON" EXPECT_WIDTH="$EXPECT_WIDTH" EXPECT_HEIGHT="$EXPECT_HEIGHT" \
  EXPECT_FPS="$EXPECT_FPS" EXPECT_DURATION="$EXPECT_DURATION" DURATION_TOL="$DURATION_TOL" "$PYTHON_BIN" - <<'PY'
import json, os
from fractions import Fraction

d = json.loads(os.environ["PROBE_JSON"])
env = os.environ.get
video, has_audio = None, False
for s in d.get("streams", []):
    print(f"  • Stream {s['index']}: {s['codec_type']} ({s['codec_name']}) {s.get('width','')}x{s.get('height','')} @ {s.get('r_frame_rate','')} fps | {s.get('duration','')}s")
    if s["codec_type"] == "video" and video is None:
        video = s
    has_audio = has_audio or s["codec_type"] == "audio"
print("@@AUDIO=" + ("1" if has_audio else "0"))
if video is None:
    print("@@FAIL No video stream.")
else:
    if env("EXPECT_WIDTH") and int(video.get("width", 0)) != int(env("EXPECT_WIDTH")):
        print(f"@@FAIL Width {video.get('width')} != expected {env('EXPECT_WIDTH')}.")
    if env("EXPECT_HEIGHT") and int(video.get("height", 0)) != int(env("EXPECT_HEIGHT")):
        print(f"@@FAIL Height {video.get('height')} != expected {env('EXPECT_HEIGHT')}.")
    if env("EXPECT_FPS"):
        fps = float(Fraction(video.get("r_frame_rate", "0/1")))
        if abs(fps - float(env("EXPECT_FPS"))) > 0.01:
            print(f"@@FAIL Frame rate {fps:g} != expected {env('EXPECT_FPS')}.")
if env("EXPECT_DURATION"):
    dur = float(d.get("format", {}).get("duration") or (video or {}).get("duration") or 0)
    if abs(dur - float(env("EXPECT_DURATION"))) > float(env("DURATION_TOL")):
        print(f"@@FAIL Duration {dur:.3f}s differs from expected {env('EXPECT_DURATION')}s by more than {env('DURATION_TOL')}s.")
PY
)"
HAS_AUDIO=0
while IFS= read -r line; do
  case "$line" in
    "@@AUDIO="*) HAS_AUDIO="${line#@@AUDIO=}" ;;
    "@@FAIL "*) fail "${line#@@FAIL }" ;;
    *) echo "$line" ;;
  esac
done <<< "$GATE1_OUT"

# 2. Audio Loudness (EBU R128)
echo -e "\n[Gate 2/5] Integrated Loudness (EBU R128)${EXPECT_LUFS:+, target ${EXPECT_LUFS} LUFS ±${LUFS_TOL} LU}:"
if [[ "$HAS_AUDIO" != "1" ]]; then
  if [[ "$ALLOW_SILENT" == true ]]; then
    echo "  • No audio stream (silent deliverable allowed)."
  else
    problem "No audio stream; loudness not measured (pass --allow-silent for silent deliverables)."
  fi
else
  EBU_OUT="$(ffmpeg -hide_banner -nostats -i "$VIDEO_PATH" -af ebur128=framelog=quiet -f null - 2>&1 || true)"
  SUMMARY="$(printf '%s\n' "$EBU_OUT" | grep -A 3 "Integrated loudness:" || true)"
  if [[ -z "$SUMMARY" ]]; then
    problem "Loudness summary not found in ffmpeg output."
  else
    printf '%s\n' "$SUMMARY" | sed 's/^/  /'
    MEASURED="$(printf '%s\n' "$SUMMARY" | awk '$1 == "I:" {print $2; exit}')"
    if [[ -n "$EXPECT_LUFS" ]]; then
      if [[ -n "$MEASURED" ]] && "$PYTHON_BIN" -c "import sys; sys.exit(0 if abs(float(sys.argv[1]) - float(sys.argv[2])) <= float(sys.argv[3]) else 1)" "$MEASURED" "$EXPECT_LUFS" "$LUFS_TOL"; then
        echo "  ✅ Within target."
      else
        fail "Integrated loudness ${MEASURED:-unknown} LUFS is outside ${EXPECT_LUFS} ±${LUFS_TOL} LU."
      fi
    fi
  fi
fi

# 3. Black frame detection (advisory: dark transitions can be intentional)
echo -e "\n[Gate 3/5] Black Screen Gap Audit:"
BLACK_GAPS=$(ffmpeg -i "$VIDEO_PATH" -vf "blackdetect=d=0.3:pix_th=0.05" -f null - 2>&1 | grep "blackdetect" || true)
if [[ -n "$BLACK_GAPS" ]]; then
  echo "  ⚠️ Notice: Dark periods detected (inspect timestamps to confirm intentional transitions):"
  echo "$BLACK_GAPS" | sed 's/^/    /'
else
  echo "  ✅ Zero unintended black frames detected."
fi

# 4. Overall size & bitrate
echo -e "\n[Gate 4/5] Container Metrics:"
ffprobe -v error -show_entries format=duration,size,bit_rate -of json "$VIDEO_PATH" | "$PYTHON_BIN" -c "
import json, sys
f = json.load(sys.stdin)['format']
def num(key, scale, unit, fmt):
    try:
        return fmt.format(float(f[key]) / scale) + unit
    except (KeyError, ValueError):
        return 'n/a'
print('  • Duration: ' + num('duration', 1, 's', '{:.2f}'))
print('  • Size: ' + num('size', 1024, ' KB', '{:.1f}'))
print('  • Bitrate: ' + num('bit_rate', 1000, ' kbps', '{:.1f}'))
"

# 5. Earshot Acoustic Verification
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
EARSHOT_BIN="$REPO_ROOT/.venv/bin/earshot"
if [[ -x "$EARSHOT_BIN" && "$HAS_AUDIO" == "1" ]]; then
  echo -e "\n[Gate 5/5] Earshot Acoustic & Spectral Verification:"
  "$EARSHOT_BIN" measure "$VIDEO_PATH" | sed 's/^/  /'
fi

echo -e "\n=========================================================="
if [[ "$FAILURES" -gt 0 ]]; then
  echo "❌ QA FAILED: $FAILURES expectation(s) not met."
  echo "=========================================================="
  exit 2
fi
echo "✅ QA Verification Complete."
echo "=========================================================="

