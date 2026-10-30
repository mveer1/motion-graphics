# Phase 5: Veo Integration Strategy & Evaluation

> **Assessment:** How to leverage Google Veo / AI video generation in the Motion Graphics pipeline without compromising programmatic precision.

---

## 1. Role Division: Procedural Animation vs. AI Generation

| Capability | Programmatic Pipeline (HyperFrames + SVG) | AI Video Generation (Veo) |
|---|---|---|
| **Mathematical precision** | ✅ Exact coordinates, graphs, equations | ❌ Hallucinates geometry & numbers |
| **Diagram topology** | ✅ Exact network nodes & edge graphs | ❌ Non-deterministic node layouts |
| **Data synchronization** | ✅ Millisecond-accurate audio sync | ❌ Uncontrollable internal pacing |
| **Cinematic textures & atmosphere** | ❌ Hard to simulate realistic organic 3D | ✅ Photorealistic light, fluids, cosmic visuals |
| **Establishing / Intro shots** | ⚠️ Flat / synthetic | ✅ Engaging cinematic metaphors |
| **Transitions & Backgrounds** | ⚠️ Static or geometric | ✅ Subtle flowing particles, nebulae, depth |

> **Architectural Rule:** Never use Veo for labels, equations, exact network architectures, or quantitative curves. Use Veo **only** for atmospheric backgrounds, cinematic intros/outros, or conceptual visual metaphors.

---

## 2. Access Audit & Practical Availability

1. **Current Environment Status:**
   - Antigravity provides access to conversational Gemini models.
   - Antigravity session does **not** expose Vertex AI API keys, Google Cloud project billing credentials, or direct Veo API client endpoints.
   - No `GEMINI_API_KEY` or `GOOGLE_API_KEY` is present in the shell environment.
   - Google AI Pro subscription provides access to consumer / web interfaces (Gemini Advanced, Flow), but not an automated billable API.

2. **Classification:**
   - **Mode 1 (Available now): Manual Generation & Import**
     - User generates short 5s–10s video clips in the Google web interface (e.g., prompt: *"Cosmic particle simulation flowing forward through dark digital space, 4k cinematic lighting, subtle blue and gold"*).
     - User downloads MP4 and places it into `assets/generated/`.
     - Pipeline ingests it as an animated background or transitional clip.
   - **Mode 2 (Requires approval & billing): Google GenAI / Vertex AI SDK**
     - Requires a Google Cloud project with Vertex AI enabled or a paid Gemini Developer API key.
     - We will NOT call paid APIs or create billable resources without your explicit approval.

---

## 3. Supported Ingestion Workflow (Mode 1)

When an external clip is placed into `assets/generated/<name>.mp4`:

### A. Preflight normalization with FFmpeg
```bash
# Normalize to project specs: 1280x720, 30fps, strip audio
ffmpeg -y -i assets/generated/intro-bg.mp4 \
  -vf "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=30" \
  -an -c:v libx264 -preset fast -crf 20 \
  assets/generated/intro-bg-normalized.mp4
```

### B. Ingest into HyperFrames composition
In `index.html`:
```html
<!-- Atmospheric background video under SVG overlay -->
<video src="../assets/generated/intro-bg-normalized.mp4"
       data-start="0"
       data-duration="7.275"
       muted
       style="position: absolute; inset: 0; width: 1280px; height: 720px; object-fit: cover; opacity: 0.28; filter: blur(2px);">
</video>
<!-- Sharp programmatic SVG graphics render on top -->
<svg style="position: absolute; inset: 0; z-index: 10;"> ... </svg>
```

This hybrid workflow gives the best of both worlds: photorealistic cinematic depth underneath, with pixel-perfect, crisp vector mathematics on top.

