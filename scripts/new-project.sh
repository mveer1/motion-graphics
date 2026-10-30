#!/usr/bin/env bash
# ==============================================================================
# Motion Lab: Project Scaffolder
# Usage: ./scripts/new-project.sh <project-slug> ["Project Title"]
# Example: ./scripts/new-project.sh distributed-consensus-raft "How Does Raft Reach Consensus?"
# ==============================================================================
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -lt 1 ]]; then
  echo "Usage: ./scripts/new-project.sh <project-slug> [\"Project Title\"]"
  echo "Example: ./scripts/new-project.sh distributed-consensus-raft \"How Does Raft Reach Consensus?\""
  exit 1
fi

SLUG="$1"
TITLE="${2:-${SLUG//-/ }}"
# Title case transformation
TITLE="$(python3 -c "import sys; print(sys.argv[1].title())" "$TITLE")"

# Validate slug format
if ! [[ "$SLUG" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "Error: Slug '$SLUG' must be lowercase alphanumeric with hyphens (kebab-case)." >&2
  exit 1
fi

PROJECT_DIR="$BASE_DIR/projects/$SLUG"

if [[ -d "$PROJECT_DIR" ]]; then
  echo "Error: Project directory '$PROJECT_DIR' already exists." >&2
  exit 1
fi

echo "============================================================"
echo "🚀 SCAFFOLDING NEW MOTION LAB PROJECT: $SLUG"
echo "============================================================"
echo "  • Directory: projects/$SLUG"
echo "  • Title:     $TITLE"
echo "  • Voice:     am_adam @ 1.15x speed (configurable)"

mkdir -p "$PROJECT_DIR/src"
mkdir -p "$PROJECT_DIR/audio"
mkdir -p "$PROJECT_DIR/renders"

# 1. Generate research.json from template
python3 -c "
import json
with open('$BASE_DIR/templates/research-template.json') as f:
    data = json.load(f)
data['metadata']['topic_id'] = '$SLUG'
data['metadata']['title'] = '$TITLE'
data['acoustic_guidance']['speech_rate'] = 1.15
with open('$PROJECT_DIR/research.json', 'w') as f:
    json.dump(data, f, indent=2)
"
echo "  ✅ Created: projects/$SLUG/research.json"

# 2. Generate research.md from template
sed -e "s/{{TITLE}}/$TITLE/g" \
    -e "s/{{TOPIC_ID}}/$SLUG/g" \
    -e "s/{{DOMAIN}}/computer_systems/g" \
    -e "s/{{DIFFICULTY}}/intermediate/g" \
    -e "s/{{TARGET_DURATION}}/30.0/g" \
    -e "s/{{MIN_DURATION}}/25.0/g" \
    -e "s/{{MAX_DURATION}}/40.0/g" \
    "$BASE_DIR/templates/research-template.md" > "$PROJECT_DIR/research.md"
echo "  ✅ Created: projects/$SLUG/research.md"

# 3. Generate src/narration.json
cat <<EOF > "$PROJECT_DIR/src/narration.json"
{
  "scenes": [
    {
      "id": "s1",
      "title": "The Problem",
      "text": "State the core problem and why it matters."
    },
    {
      "id": "s2",
      "title": "The Mechanism",
      "text": "Explain how the internal mechanism or algorithm works."
    },
    {
      "id": "s3",
      "title": "Resolution",
      "text": "Demonstrate the final outcome and why it guarantees correctness."
    }
  ]
}
EOF
echo "  ✅ Created: projects/$SLUG/src/narration.json"

# 4. Generate starter src/index.html with GSAP 3, mulberry32, sceneFade
cat <<'EOF' > "$PROJECT_DIR/src/index.html"
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #080c14;
      width: 1280px; height: 720px;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
    }
    #root {
      position: relative;
      width: 1280px; height: 720px;
    }
    .scene {
      position: absolute;
      inset: 0;
      opacity: 0;
      pointer-events: none;
    }
    .scene-title {
      position: absolute;
      top: 100px; left: 0; right: 0;
      text-align: center;
      font-size: 48px;
      font-weight: 700;
      color: #f0f6fc;
      letter-spacing: -0.02em;
    }
    .scene-subtitle {
      position: absolute;
      top: 170px; left: 0; right: 0;
      text-align: center;
      font-size: 20px;
      color: #8b949e;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }
    .canvas-stage {
      position: absolute;
      top: 240px; left: 0; right: 0; bottom: 0;
      display: flex; justify-content: center; align-items: center;
    }
  </style>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
</head>
<body>
<div id="root"
     data-composition-id="root"
     data-width="1280"
     data-height="720"
     data-fps="30"
     data-duration="30.0">

  <!-- Scene 1 -->
  <div class="scene" id="scene1">
    <div class="scene-title">Scene 1 Title</div>
    <div class="scene-subtitle">Subtitle / Core Insight</div>
    <div class="canvas-stage">
      <svg width="800" height="400" viewBox="0 0 800 400" id="stage-svg-1">
        <circle cx="400" cy="200" r="40" fill="#58a6ff" id="s1-circle" />
      </svg>
    </div>
  </div>

  <!-- Scene 2 -->
  <div class="scene" id="scene2">
    <div class="scene-title">Scene 2 Title</div>
    <div class="scene-subtitle">Internal Mechanism</div>
    <div class="canvas-stage">
      <svg width="800" height="400" viewBox="0 0 800 400" id="stage-svg-2">
        <rect x="360" y="160" width="80" height="80" rx="8" fill="#3fb950" id="s2-rect" />
      </svg>
    </div>
  </div>

  <!-- Scene 3 -->
  <div class="scene" id="scene3">
    <div class="scene-title">Scene 3 Title</div>
    <div class="scene-subtitle">Resolution & Convergence</div>
    <div class="canvas-stage">
      <svg width="800" height="400" viewBox="0 0 800 400" id="stage-svg-3">
        <polygon points="400,160 440,240 360,240" fill="#e3b341" id="s3-poly" />
      </svg>
    </div>
  </div>
</div>

<script>
// Deterministic mulberry32 PRNG (NO Math.random)
function mulberry32(a) {
  return function() {
    let t = a += 0x6D2B79F5;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
const rand = mulberry32(42);

// Master GSAP Timeline (paused: true, registered on window.__timelines['root'])
const tl = gsap.timeline({ paused: true });
const FADE = 0.5;

function sceneFade(outId, inId, at) {
  tl.to(`#${outId}`, { opacity: 0, duration: FADE, ease: 'power1.inOut' }, at - FADE / 2);
  tl.to(`#${inId}`,  { opacity: 1, duration: FADE, ease: 'power1.inOut' }, at - FADE / 2);
}

// Initial scene
tl.to('#scene1', { opacity: 1, duration: 0.01 }, 0.0);
tl.fromTo('#s1-circle', { scale: 0.5, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.8 }, 0.2);

// Transition placeholders (update timestamps after running scripts/build-audio.py)
sceneFade('scene1', 'scene2', 10.0);
tl.fromTo('#s2-rect', { rotation: -45, opacity: 0 }, { rotation: 0, opacity: 1, duration: 0.8 }, 10.3);

sceneFade('scene2', 'scene3', 20.0);
tl.fromTo('#s3-poly', { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.8 }, 20.3);

window.__timelines = window.__timelines || {};
window.__timelines['root'] = tl;
</script>
</body>
</html>
EOF
echo "  ✅ Created: projects/$SLUG/src/index.html"

echo "============================================================"
echo "🎉 PROJECT SCAFFOLDED SUCCESSFULLY!"
echo "Next Steps:"
echo "  1. Complete research dossier: projects/$SLUG/research.json"
echo "  2. Validate research:         python3 scripts/validate-research.py projects/$SLUG"
echo "  3. Build audio clips:         python3 scripts/build-audio.py $SLUG"
echo "  4. Build & render video:      ./scripts/build-project.sh $SLUG"
echo "============================================================"

