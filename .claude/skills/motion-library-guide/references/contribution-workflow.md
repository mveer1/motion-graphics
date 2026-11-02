# Capability Catalogue Contribution Workflow

This protocol outlines the 5-stage lifecycle for discovering, vetting, testing, documenting, and approving new animation libraries, visual effects, and recipes.

---

## Stage 1: Needs Assessment & Redundancy Check
1. **Search Existing Catalogue First:**
   ```bash
   python3 scripts/motion-catalogue.py search --query "<capability>"
   ```
2. **Preference for Existing Implementations:**
   - Always prefer GSAP 3 + Native SVG / Canvas 2D over importing external packages.
   - If the desired effect can be achieved using an SVG filter, clipPath, or GSAP tween, author a **Recipe** rather than proposing a new **Library**.
3. **Redundancy Filter:**
   - Redundant libraries (e.g. Anime.js, Popmotion, Velocity.js) that overlap with GSAP are automatically marked `blocked`.

---

## Stage 2: Licensing & Documentation Audit
1. Locate upstream repository and primary `LICENSE` file.
2. Confirm SPDX identifier (e.g. `MIT`, `Apache-2.0`, `BSD-3-Clause`).
3. Ensure `commercial_use: true` applies to generated video renders.
4. If license is ambiguous or proprietary, mark `licensing.status: "unverified"` and restrict status to `proposed`.

---

## Stage 3: Sandbox Benchmarking on Apple Silicon
Before submitting a record for approval:
1. Create a minimal test composition under `tests/test-sandbox/index.html`.
2. Anchor animation to `window.__timelines['root']` with `{ paused: true }`.
3. Render visual track:
   ```bash
   hyperframes render tests/test-sandbox --fps 30 --low-memory-mode --output tests/test-sandbox.mp4
   ```
4. Verify resource utilization:
   - Run `top -l 1 | grep Chromium` or check Activity Monitor to ensure memory stays $\le$ 1500 MB.
   - Inspect output video with `scripts/run-qa-gates.sh` to confirm 0 black frames and stable framerate.

---

## Stage 4: Catalogue Schema Authoring
1. **Add Library Record:** Create `catalogue/data/libraries/<id>.json` conforming to `catalogue/schemas/library.schema.json`.
2. **Add Effect Record:** Create `catalogue/data/effects/<id>.json` conforming to `catalogue/schemas/effect.schema.json`.
3. **Add Recipe Record:** Create `catalogue/data/recipes/<id>.json` conforming to `catalogue/schemas/recipe.schema.json`. Ensure parameters, code snippets, fallbacks, and validation steps are fully populated.

---

## Stage 5: Validation & Export
1. Run automated schema and reference validation:
   ```bash
   python3 scripts/motion-catalogue.py validate
   ```
   Must exit with code 0 (`[PASS] All records, schemas, and cross-references are valid`).
2. Run test suite:
   ```bash
   python3 tests/test-motion-catalogue.py
   ```
3. Export compiled index:
   ```bash
   python3 scripts/motion-catalogue.py export
   ```
4. Submit PR or commit with detailed justification.

