---
name: asset-engine
description: Acquire, track and reuse visual assets with provider-independent jobs. Use when a beat needs a texture, plate, image or clip: choose programmatic, procedural, imported or generated; register provenance; reuse what exists; run asynchronous jobs with bounded retries; export into the project. Never needs a credential for the default workflow.
---

# Asset Engine

`scripts/assets.py` over `src/pipeline/assets/`. Contracts: `specs/asset-spec.json` (capabilities, asset, job).

## Choose the medium first

| Need | Use | Why |
| --- | --- | --- |
| numbers, charts, counters, diagrams, labels, exact type | code (HyperFrames/GSAP/SVG) | deterministic and exact; generation would only add error |
| paper, grain, halftone, haze, caustics, silhouette layers, torn sheets | `assets.py procedural` | offline, seeded, byte-reproducible |
| a file you obtained elsewhere (Veo/Flow download, stock, photo) | `assets.py import` | records prompt, tool and licence with the file |
| photographic or complex scenes that code cannot make | `assets.py generate` with a configured provider | needs a key; check cost and terms first |

## Commands

`providers` (what each can do, whether it is usable now, how far it was verified), `plan <task> --aspect 16:9` (which providers fit and why not), `procedural|import|generate`, `jobs`/`resume`, `list`, `show`, `approve|reject`, `export <project> <ids> --name ...` (copies into `<project>/src/assets/` because HyperFrames serves only the composition folder, and writes a manifest).

## Rules

- **Reuse before generating.** An identical request (task, provider, model, prompt, params, reference hashes) resolves to the existing asset and calls no provider.
- **Jobs are data.** A failed or timed-out job is recorded with a typed error; the next provider in the chain is tried; the project continues. A job with a remote id is polled, never re-submitted, so a restart cannot pay twice. Retries are bounded and only for errors the adapter marks retryable.
- **Secrets**: environment variables only (named in `capabilities.auth.env_var`; for kie.ai `KIE_API_KEY`). Never in files, prompts, logs, localStorage or job records; `secrets.redact` runs on every record. Adapters send keys only to the API host, never to result CDNs.
- **Verification levels are honest.** `kie` is `partial`: status polling and the envelope were checked against the official docs; the create path and per-model inputs were not. MuAPI has no adapter because its docs could not be read. Do not run a live job without the user's key and approval, and never claim a generated result you did not produce.
- **Approve before use.** New assets are `pending`; look at them, then `approve`. `rejected` assets are never reused.
- **Label what it is.** Procedural imagery is stylised, not photographic and not archival; say so in the brief's constraints.

## Adding a provider

Subclass `base.Provider` (capabilities, available, submit, status, fetch), declare capabilities from documented facts only (no invented model lists or prices), register it in `providers/__init__.py`, and add a stub-server contract test like `TestKie`.
