---
name: technical-researcher
description: Conducts rigorous technical investigation, formulates visual metaphors, and authors schema-validated research dossiers (research.json and research.md) for motion graphics.
---

# Technical Researcher Skill

This skill governs Stage 0 of the motion graphics lifecycle: deep factual research, mathematical ground truth verification, visual metaphor design, and schema validation.

## 1. Deliverables per Topic
Every researched topic under `projects/<slug>/` must contain:
1. `research.json`: Strict JSON data model validated against `specs/research-spec.json`.
2. `research.md`: Comprehensive academic and pedagogical narrative explaining the domain, formulas, and visual transitions.

---

## 2. Strict Schema Rules for `research.json`

When authoring `research.json`, adhere strictly to these invariants:

### A. Metadata
- `topic_id`: Kebab-case slug (e.g. `btree-database-indexing`).
- `domain`: Must be one of:
  `[deep_learning, machine_learning, computer_systems, distributed_systems, database_internals, networking, cryptography, algorithms_data_structures, physics_mathematics, software_engineering]`
- `difficulty`: `introductory`, `intermediate`, or `advanced`.
- `target_duration_sec`: Object with `{ "min": float, "max": float, "target": float }`.
- `canonical_sources`: Primary papers, RFCs, or documentation (with `title`, `authors`, `year`, `source_type`, `url`).

### B. Pedagogy & Ground Truth
- `pedagogy`: Must provide `problem_statement`, `core_thesis`, `mental_model`, `key_takeaway`, `verified_claims` (>= 2), and `anti_patterns`.
- `ground_truth.entities`: Math/system entities with `id`, `name`, `symbol_latex`, and `role`.
- `ground_truth.equations`: Core relations with `id`, `latex`, and `spoken_form` (plain words for Kokoro TTS).
- `ground_truth.algorithmic_steps`: Discrete state transitions with `step_number`, `phase_name`, `mathematical_operation`, and `state_effect`.

### C. Visual Metaphors & Archetypes
- `visual_archetype`: **MUST be one of the following exact enum strings**:
  - `node_network_graph`
  - `vector_pulse_flow`
  - `curved_landscape_descent`
  - `b_tree_split_hierarchy`
  - `state_machine_transition`
  - `matrix_grid_transform`
  - `ring_buffer_pipeline`
  - `geometric_gauge_meter`
  - `layer_stack_isometric`
  - `scatter_cluster_distribution`
- Include: `svg_primitives`, `spatial_anchor`, `motion_pattern`, and `color_token`.

### D. Acoustic Guidance
- `recommended_voice`: `"am_adam"` (technical), `"af_bella"` (conversational), or `"bm_george"` (academic).
- `speech_rate`: `1.15` (standard default).
- `inter_scene_pause_sec`: `0.5`.
- `phonetic_lexicon`: Array of `{ "term": "...", "phonetic_respelling": "...", "rationale": "..." }`.

### E. Scene Blueprint
- 3 to 5 progressive learning scenes.
- `scene_id`: **MUST match regex `^s[1-9][0-9]*$`** (e.g., `"s1"`, `"s2"`, `"s3"`, `"s4"`).
- Each scene requires: `scene_id`, `title`, `target_duration_sec`, `pedagogical_objective`, `visual_action`, and `active_entities`.

---

## 3. Validation Gate
Always validate the research dossier prior to storyboarding or scriptwriting:
```bash
python3.12 scripts/validate-research.py projects/<slug>
```
Only proceed to Stage 1 when validation exits with code 0 and reports `RESEARCH DOSSIER VALIDATION PASSED`.
