# Component Placement Policy

This policy defines the authoritative placement rules for every type of file, module, dependency, asset, and metadata artifact in the workspace.

---

## 1. Domain Separation Taxonomy

All workspace files and components must reside in their designated domain:

| Domain | Allowed Locations | Rules & Constraints |
|---|---|---|
| **1. Workspace-Owned Source Code & Config** | `src/`, `scripts/`, `specs/`, `templates/` | Standard workspace source files. Must be strictly formatted, modular, and committed to version control. No hardcoded absolute personal paths. |
| **2. Agent Skills & Supporting Resources** | `.agents/skills/<skill-name>/` | Contains `SKILL.md` with YAML frontmatter, `references/`, `examples/`, `scripts/`. Skills must be modular and documented in `catalogue/data/skills/`. |
| **3. Third-Party Dependencies** | `.venv/`, Host Package Managers (`brew`, `npm`), `assets/vendor/` | **Never** copy arbitrary third-party code into the repo without licence check and explicit approval. Prefer declared virtualenv / global packages. If vendoring is unavoidable, store under `tools/<name>/` or `assets/vendor/` with upstream LICENSE. |
| **4. Reusable Motion Components** | `catalogue/data/recipes/`, `catalogue/data/effects/`, `templates/` | Modular GSAP animation snippets, SVG templates, and effect definitions. Must be registered in the capability catalogue. |
| **5. Generated Assets & Build Outputs** | `projects/*/renders/`, `out/`, `audio/`, `logs/`, `tests/_work/` | Ephemeral build outputs. Never checked into git repository root as source code; isolated to build artifact directories. |
| **6. Secrets & Machine-Specific Config** | `.env`, Keychain, Host Env Vars | **STRICTLY PROHIBITED** from committing to repository. Zero API keys, bearer tokens, private keys, or credentials may appear in source, catalogue, or logs. |
| **7. Registry Metadata & Architecture Docs** | `catalogue/`, `ARCHITECTURE.md`, `AGENTS.md`, `README.md` | Machine-readable schemas, records, and human-readable architecture documentation. Must be kept strictly synchronized via `scripts/workspace-governance.py`. |

---

## 2. Vendoring Policy

1. **Declared over Vendored:** Third-party libraries should be declared as dependencies (in Python virtual environment, system brew, or npm global) rather than committed directly into the source tree.
2. **License Clearance:** Before vendoring any tool (e.g. `tools/earshot`), verify that the licence allows commercial distribution without viral obligations (`MIT`, `Apache-2.0`, `BSD-3-Clause`).
3. **No Redundant Bundles:** Do not introduce competing libraries (e.g. Anime.js when GSAP is approved).

---

## 3. Secret Protection Standard

1. **Zero Secret Footprint:** No secrets, tokens, passwords, private keys, or API tokens are permitted in catalogue records, source files, or commit logs.
2. **Dynamic Injection:** Any external API needing authentication must read keys from local environment variables or macOS Keychain at runtime.
3. **Automated Audit:** The `scripts/workspace-governance.py` Gate 6 scan checks all catalogue records for sensitive string patterns and flags violations immediately.
