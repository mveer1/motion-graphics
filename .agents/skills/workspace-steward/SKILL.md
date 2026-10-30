---
name: workspace-steward
description: Workspace-wide governance over component discovery, placement policy, registration, licensing audit, architecture documentation, and drift detection.
---

# Workspace Steward Skill

The `workspace-steward` skill governs the discovery, creation, installation, placement, registration, integration, modification, and retirement of all workspace components.

---

## Quick References

- **Placement Policy:** Read [`references/component-placement-policy.md`](./references/component-placement-policy.md) for authoritative rules across the 7 workspace domains.
- **Component Lifecycle:** Read [`references/component-lifecycle.md`](./references/component-lifecycle.md) for the 10-stage evaluation and promotion protocol.
- **Governance & Safety Rules:** Read [`references/governance-rules.md`](./references/governance-rules.md) for skill handoffs and security guardrails.
- **Validation CLI:** Run `python3 scripts/workspace-governance.py` for automated drift and schema auditing.

---

## 1. When to Use This Skill

Activate `workspace-steward` whenever you need to:
1. **Introduce a New Component:** Propose or install a library, CLI tool, agent skill, subagent, plugin, or shared template.
2. **Verify Component Placement:** Determine where a newly created file belongs according to the 7-domain placement policy.
3. **Enforce Registration:** Author and validate a schema record under `catalogue/data/` for any newly added or discovered component.
4. **Update Architecture Documentation:** Keep `ARCHITECTURE.md` and `AGENTS.md` synchronized with material system changes.
5. **Detect Workspace Drift:** Run automated checks to identify unregistered tools/skills or orphaned files.
6. **Retire or Deprecate Components:** Transition outdated components to `deprecated` or `blocked` status without breaking dependent pipelines.

---

## 2. Standard Governance Workflow

Whenever modifying or introducing components:

```bash
# 1. Search existing registry before proposing new dependencies:
python3 scripts/motion-catalogue.py search --query "<name_or_keyword>"

# 2. Check component placement and author schema record:
# Create catalogue/data/<collection>/<id>.json

# 3. Run governance drift detection and schema validation:
python3 scripts/workspace-governance.py

# 4. Re-export updated catalogue index manifest:
python3 scripts/motion-catalogue.py export
```

---

## 3. Skill Coordination & Clear Handoffs

To eliminate duplicate responsibilities across skills:

1. **`workspace-steward` (This Skill):**
   - Owns workspace-wide placement, registration, dependency vetting, architecture documentation, and drift detection.
   - Standard entry point for adding tools, skills, libraries, or shared assets.
2. **`motion-library-guide`:**
   - Owns capability catalogue queries and recipe recommendations for animation choreography.
   - When a required effect or library is missing from the catalogue, delegates to `workspace-steward`.
3. **`motion-graphics-designer`:**
   - Owns aesthetic design system, color tokens, typography rules, canvas layout, and scene execution in `src/index.html`.
