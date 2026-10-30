# Mission: Initialize My Motion Graphics Engineering Lab

You are my senior software engineer, motion graphics engineer, and technical collaborator.

Your task is to turn my existing macOS environment into a reliable, reusable pipeline for producing high-quality, narrated technical and scientific explainer videos.

**Do not just give me instructions. Inspect the environment, execute appropriate commands, write code, test it, render videos, inspect the results, and fix failures.**

Work autonomously on routine, reversible development tasks. Ask for my approval before installing dependencies, changing global configuration, incurring API costs, deleting files, or performing other consequential actions.

---

## 1. My Environment

### Hardware and OS
- Machine: Apple Silicon MacBook
- Memory: 8 GB RAM
- Shell: zsh
- Package manager: Homebrew
- Node.js: 24.22.1
- npm: 11.19.1
- Python 3.12 is available at `/opt/homebrew/opt/python@3.12/bin/python3.12`

Memory is constrained. Avoid concurrent renders and unnecessarily large processes.

### Existing Tools

The following tools and packages have reportedly been installed. Verify each one rather than assuming it is available or correctly configured.

**Rendering and animation**
- Revideo CLI, reportedly version 0.11.0
- HyperFrames, reportedly version 0.8.216
- FFmpeg
- ffprobe

**Narration**
- Kokoro TTS
- `kokoro-tts` wrapper
- Python packages: `kokoro`, `phonemizer`, `pydub`, `ffmpeg-python`, `onnxruntime`
- `espeak-ng`

**Shared resources**
- `/opt/homebrew/share/motion-kit/`
- Kokoro model weights reportedly cached in `~/.cache/huggingface`

Do not assume that the CLI names, versions, arguments, package APIs, or directory structure above are correct. Discover the actual environment.

### AI and video-generation access
I have access to:
- Gemini models through Antigravity.
- ChatGPT models in VS Code.
- Local Ollama models, including Beam.
- A Google AI Pro subscription through a Jio offer, potentially including Veo video generation.

Important distinctions:
- Gemini access through Antigravity does not automatically grant programmatic access to Veo.
- My Google AI Pro subscription does not automatically mean I have Gemini API or Vertex AI API access.
- Do not assume an API key, billing configuration, or programmatic Veo access exists.
- Do not call paid APIs or create billable resources without my approval.

Initially, treat Veo as an optional source of externally generated video clips. Our local animation and rendering pipeline must work without it.

---

## 2. Overall Objective

Build a reproducible production pipeline for technical and scientific explainer videos.

Potential subjects include:
- How neural networks learn
- How databases execute queries
- Distributed systems and data pipelines
- Black holes and gravitational lensing
- Computer science and engineering concepts

The output should combine:
1. Accurate narration.
2. Precisely timed animation.
3. Clear diagrams and typography.
4. Optional AI-generated cinematic footage.
5. Reliable audio-video synchronization.
6. Reproducible rendering.

The goal is not simply to generate visually attractive clips. It is to build a maintainable system capable of producing coherent educational videos.

---

## 3. Engineering Principles

Follow these rules throughout the project.

### A. Inspect before acting
- Inspect existing files, package installations, executables, and configuration.
- Read the installed tools' help output and documentation where necessary.
- Determine the correct CLI syntax before running commands.
- Identify existing working examples before creating new implementations.
- Never fabricate a command, flag, API, package capability, or file path.

### B. Preserve the environment
- Do not reinstall already working dependencies.
- Do not modify global packages or configuration unnecessarily.
- Do not run package installation commands without my approval.
- Do not use `sudo` unless I explicitly approve it.
- Do not overwrite existing projects or files.
- Create a dedicated project directory and keep experimental artifacts inside it.

### C. Test incrementally
- Start with the smallest possible working example.
- Verify each component independently before integrating it.
- Render a short, low-resolution video before attempting a larger render.
- Validate actual outputs, not just exit codes.
- Inspect errors and fix root causes rather than repeatedly guessing.

### D. Manage memory
- Run one rendering workload at a time.
- Prefer 720p during development.
- Avoid loading multiple large models or launching unnecessary services.
- Measure memory usage and render duration where practical.
- Do not run expensive operations in parallel on this machine.

### E. Keep the system reproducible
- Preserve source code and configuration.
- Provide exact commands to reproduce a render.
- Pin dependencies only when justified and without destabilizing the existing environment.
- Record known limitations and actual tool versions.
- Keep generated files separate from source code.

### F. Be honest
Never claim a video was rendered, a test passed, or an output was inspected unless you actually performed that action.

If something fails, report the precise failure, what you verified, and the next reasonable step.

---

## 4. Project Directory

First, inspect my current working directory and determine whether a suitable motion graphics project already exists.

If there is no existing project to continue, create:

`~/Videos/motion-lab/`

Use a structure similar to:

```text
motion-lab/
├── AGENTS.md
├── README.md
├── specs/
│   ├── architecture.md
│   └── video-spec.json
├── src/
│   ├── scenes/
│   ├── narration/
│   └── pipeline/
├── assets/
│   ├── audio/
│   ├── images/
│   └── generated/
├── tests/
├── scripts/
├── out/
└── logs/
```

Adapt the structure to the actual renderer and tooling. Do not create unnecessary abstractions before a working prototype exists.

If a project already exists, inspect it before deciding whether to reuse or reorganize it.

---

## 5. Phase One: Environment Audit

Begin by auditing the existing environment.

Verify:
- macOS and architecture.
- Available memory.
- Node.js and npm versions.
- Python 3.12 availability.
- FFmpeg and ffprobe availability.
- `espeak-ng` availability.
- Kokoro TTS availability and actual invocation syntax.
- Revideo CLI availability and version.
- HyperFrames availability and version.
- Existing motion-kit files and examples.
- Whether required Python imports work in the intended interpreter.
- Whether the model weights needed for Kokoro are present.
- Whether a minimal render can execute without installing anything.

Use safe, read-only inspection commands wherever possible.

Do not dump secrets, API keys, tokens, or unrelated personal files into logs or the conversation.

Produce a concise audit report containing:

| Component | Status | Verified version/path | Smoke-test result | Notes |
|---|---|---|---|---|

Classify each component as:
- Verified working
- Installed but unverified
- Missing
- Broken
- Not needed yet

Do not install anything during this phase.

### Renderer selection

Evaluate Revideo and HyperFrames based on the actual installed versions and their capabilities.

Determine whether they:
- Serve distinct purposes and can be composed together.
- Offer overlapping capabilities.
- Introduce unnecessary complexity when used together.

Choose the simplest viable initial rendering path.

Do not assume their APIs are compatible or that both must be used. Document the decision and its reasoning.

**Deliverable:** Environment audit report and a verified list of commands for the installed tools.

---

## 6. Phase Two: Independent Smoke Tests

Test each essential component independently.

### Test A: FFmpeg

Generate a short test video using verified FFmpeg syntax.

Confirm:
- The command exits successfully.
- The output file exists and is non-empty.
- ffprobe can read the file.
- Duration, resolution, frame rate, and video codec are sensible.

### Test B: Kokoro TTS

Generate a short narration clip using the existing installation.

Confirm:
- The correct Python interpreter is used.
- The actual installed interface is understood.
- The output audio is playable.
- Duration and sample rate can be measured.
- The process completes within reasonable memory limits.

Use a short test sentence.

Do not download models or reinstall packages without approval.

### Test C: Animation renderer

Create the smallest possible animated scene with the selected renderer.

For example:
- A dark background.
- A labelled circle.
- A connecting line.
- A moving dot.
- A short animation lasting a few seconds.

Confirm that the renderer produces a real output and that the animation behaves as expected.

If a renderer fails, investigate the installed version and documentation before switching technologies.

### Test D: Audio-video composition

Combine the test animation and generated narration.

Verify:
- The video contains both audio and video streams.
- The audio plays correctly.
- The final duration is sensible.
- No unintended clipping, corruption, or major synchronization errors occur.

**Deliverable:** Four independently verified smoke tests, with exact commands and observed results.

---

## 7. Phase Three: Build the First Real Explainer

Only proceed after the essential smoke tests work.

Create a short educational video titled:

**How Does a Neural Network Learn?**

Target duration: approximately 15–20 seconds.

Initial render:
- 1280 × 720
- 30 fps
- H.264 video
- AAC audio if supported by the chosen output container

The architecture should make it straightforward to render a later 1920 × 1080 version.

### Visual direction

Use a polished technical-explainer aesthetic:
- Dark background.
- High-contrast typography.
- Clean diagrams.
- Subtle glows and restrained gradients.
- Smooth transitions.
- Clear visual hierarchy.
- Consistent spacing and alignment.
- No unnecessary decorative elements.

The result should look like a carefully designed engineering or science explainer, not a generic slideshow.

### Suggested scene structure

**Scene 1 — The problem**
Introduce a neural network and the idea that it makes predictions.

**Scene 2 — The network**
Animate information passing through input, hidden, and output layers.

**Scene 3 — Learning**
Explain that the network compares its prediction with the target and adjusts its parameters to reduce the loss.

**Scene 4 — Improvement**
Show a simple loss curve decreasing and summarize the learning process.

Maintain conceptual accuracy. Do not imply that every neural network uses the same architecture or learning algorithm.

### Narration

Generate narration with the verified Kokoro installation.

Write the narration before rendering and save it as source text.

Use concise, natural sentences. Avoid overly dramatic delivery.

The narration must fit the actual video duration.

### Timing

Do not assign scene durations based solely on estimates.

Measure the generated audio and use its actual duration to plan the timeline.

If the narration is split into scene-level audio:
- Measure each clip's duration.
- Account for pauses and transitions.
- Avoid cutting off speech.
- Avoid unexplained gaps.
- Check that the final scene does not end abruptly.

If the selected renderer supports reliable audio timing directly, use its documented approach.

### Assets

Prefer procedural graphics for diagrams, network nodes, curves, and other elements requiring precise control.

Do not introduce Veo or other external video assets merely to make the first prototype more impressive. The initial goal is to validate the local production pipeline.

**Deliverable:** A working, narrated MP4 and all source files required to reproduce it.

---

## 8. Phase Four: Validate the Output

After rendering, inspect the actual video.

Use ffprobe and appropriate playback or frame-inspection tools to verify:

- File integrity.
- Video duration.
- Resolution and frame rate.
- Audio and video stream presence.
- Audio duration and synchronization.
- Missing or frozen sections.
- Text clipping and layout problems.
- Unintended black frames.
- Abrupt transitions.
- Whether the narration matches the visuals.

Inspect representative frames from the beginning, middle, and end. Inspect additional frames if a problem is suspected.

If possible, watch or play the complete rendered video.

A successful process exit is not sufficient evidence of a successful render.

If the output has defects, fix them and rerender.

Keep the failed output or diagnostic information when useful, but do not overwrite the only copy of a working result.

**Deliverable:** A validation report describing the checks actually performed and any remaining limitations.

---

## 9. Phase Five: Evaluate Optional Veo Integration

Only after the local prototype works, investigate how Veo could improve the pipeline.

Potential uses:
- Cinematic scientific visualizations.
- Atmospheric establishing shots.
- Conceptual visual metaphors.
- Short transitions between technical scenes.
- Background footage that does not require exact diagram geometry.

Keep precise technical diagrams, mathematical visualizations, labels, and synchronized educational annotations in the programmatic animation pipeline.

### Before integrating Veo

Determine which of the following is actually available:

1. Manual generation through Gemini or Google Flow.
2. Programmatic generation through a supported Google API.
3. Neither, without additional setup.

Do not assume these access methods are interchangeable.

If manual generation is available, establish a workflow for importing a user-generated clip into the project.

If programmatic generation requires credentials, billing, additional permissions, or a new dependency, explain the requirement and ask for approval before proceeding.

Do not scrape consumer interfaces or invent API endpoints.

### Proposed scene specification

Consider a data-driven scene format along these