# Motion Graphics Approval Policy & Governance

This document establishes the evaluation criteria, hardware thresholds, and licensing rules required to certify dependencies, visual effects, and animation recipes for the production pipeline.

---

## 1. Approval States

Every item in the catalogue carries one of five immutable lifecycle states:

### 1. `approved`
- **Definition:** Fully validated, production-ready, and certified for active explainer compositions.
- **Criteria:**
  1. Tested on Apple Silicon (M2, 8 GB RAM) under `hyperframes render --low-memory-mode`.
  2. Verified deterministic timeline advancement with zero frame skipping or time drift.
  3. Memory consumption strictly $\le$ 1500 MB during render execution.
  4. Verified commercial licensing (`commercial_use: true`).
  5. Paired with at least one validated recipe and automated test.

### 2. `experimental`
- **Definition:** Under active sandbox benchmarking or performance evaluation.
- **Criteria:**
  1. Code exists in a sandbox or test composition (`tests/`).
  2. Demonstrates proof-of-concept visual output, but memory profile, multi-scene stability, or edge cases are not yet finalized.
  3. **Usage Rule:** May ONLY be used in test benches; strictly forbidden in client/production releases.

### 3. `proposed`
- **Definition:** Candidate capability or library requested for technical exploration.
- **Criteria:**
  1. Solves a documented pedagogical or visual need not fulfilled by current tools.
  2. Has documented documentation URLs and proposed rendering architecture.
  3. **Usage Rule:** Cannot be used in compositions until promoted to `experimental` or `approved`.

### 4. `deprecated`
- **Definition:** Previously approved capability that is being phased out in favor of a superior, safer, or lighter approach.
- **Criteria:**
  1. Existing projects referencing it remain functional, but new projects are blocked from adopting it.
  2. Scheduled for archiving once dependent compositions are migrated.

### 5. `blocked`
- **Definition:** Explicitly rejected or prohibited dependency or effect.
- **Criteria for Blocking:**
  1. **Redundancy:** Duplicates capabilities already covered by standard stack (e.g. Anime.js vs. GSAP 3).
  2. **Non-Determinism:** Relies on unseeded timers, unintercepted `requestAnimationFrame`, or unseeded RNG.
  3. **Resource Exhaustion:** Exceeds 1.5 GB RAM ceiling on Apple Silicon or causes headless Chromium ANGLE Metal GPU hangs.
  4. **Licensing Incompatibility:** Restrictive non-commercial only (CC-NC, AGPL in proprietary distribution, or unverified terms).

---

## 2. Licensing Verification Standard

All records MUST declare:
```json
"licensing": {
  "spdx_identifier": "<SPDX-ID or formal name>",
  "status": "verified" | "unverified",
  "commercial_use": true | false,
  "attribution_required": false,
  "notes": "<Specific legal terms>"
}
```

- **Rule 1:** A library cannot be marked `approved` while `licensing.status` is `"unverified"`.
- **Rule 2:** Unverified licenses must remain explicitly marked `"unverified"` until primary source terms (e.g. LICENSE file in upstream repo) have been audited.
- **Rule 3:** Never assume a library is MIT just because it is open-source. Inspect the actual repository license file.

---

## 3. Hardware & Memory Thresholds (Apple Silicon M2, 8 GB RAM)

1. **Memory Budget:**
   - Base Chromium & OS: ~600 MB.
   - SVG DOM + GSAP timeline: ~150–250 MB.
   - Headless screenshot worker: ~300 MB.
   - **Hard Cap:** Total render memory must not exceed **1.5 GB RAM**.
2. **Frame Rate:** Strict 30.00 fps.
3. **Canvas Dimensions:** Standard 1280×720 (720p). Scaling to 1920×1080 requires explicit instruction and memory monitoring.
4. **Worker Cap:** Exactly 1 worker (`hyperframes render --low-memory-mode`). Parallel render instances are forbidden.

