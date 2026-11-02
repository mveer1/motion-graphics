"""Creative asset engine: provider-independent generation, job lifecycle and an asset library.

Layout:
  base.py        Provider interface, job states, typed errors
  secrets.py     credentials come from the environment only; redaction for logs and records
  store.py       asset library (index + content-addressed files) and job store, both plain JSON on disk
  engine.py      planning (capability matching), submission with reuse, bounded polling, retry, fallback
  providers/     procedural (offline), import (manual files), kie (docs-verified partial), mock (tests)

Contracts: specs/asset-spec.json. Nothing here is required by the programmatic workflow.
"""
