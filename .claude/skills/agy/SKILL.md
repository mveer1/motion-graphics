---
name: agy
description: Delegate low-complexity, high-volume work (summarizing long files or logs, bulk extraction, boilerplate and first drafts, mechanical edits, test-output triage) to Gemini through the Antigravity CLI `agy`, to save Claude tokens. Use before reading or generating a large amount of text yourself. Never for renders, audio, QA verdicts, creative judgment or anything secret.
---

# agy: delegate cheap work to Gemini

`agy` (Antigravity CLI 1.4.x, `~/.local/bin/agy`) runs a Gemini agent headless. It reads files in the workspace itself, so you hand it a path and a question and only its short answer enters your context. That is where the saving comes from.

## When to delegate

Delegate when the task is **well specified, low in judgment, and large in input or output**:

- Summarize or condense a long file, research dossier, transcript, log or diff to the facts you need.
- Extract structured data (lists, tables, fields) from many files, using `-s` for a schema.
- Triage test or build output: which tests failed, what the first real error is.
- Draft boilerplate with a clear template: catalogue records, JSON that a schema will check, docs sections, commit or PR text.
- Mechanical edits with an explicit rule (rename, reformat, apply the same change across files).
- First-pass lookups across the repo ("where is X configured, list file:line").

Do it yourself when the answer is a single `Grep` or a small `Read`. Every agy call carries about 12k tokens of fixed overhead on Gemini's side and takes 4 to 30 s, so it pays off only on bulk work.

## When NOT to delegate

- Anything on the render, TTS, QA or lock path: `hyperframes`, Kokoro, `studio.py build`, `session-guard.py`, loudness or frame review verdicts.
- Creative decisions, storyboard and beat design, `qa/creative-review.json` scoring, motion critique. Looking at frames is yours.
- Determinism-critical composition code (`src/index.html`, `src/studio/`) beyond mechanical edits you will review.
- Architecture, governance and catalogue approval decisions.
- Secrets, `.env`, credentials. Prompts and the files agy reads go to Google, so keep it to content you would accept sharing.
- Anything needing a shell command. Headless agy auto-denies commands.

## How to call it

Use the wrapper. It closes stdin, requests JSON, parses the result and reports denials:

```bash
.claude/skills/agy/scripts/agy-ask.sh [-m MODEL] [-w EXACT_FILE]... [-s SCHEMA] "prompt"
```

```bash
# summarize
.claude/skills/agy/scripts/agy-ask.sh "Read projects/<slug>/research.md. Give 10 bullets of the claims that carry numbers, with the source name."

# structured extraction
.claude/skills/agy/scripts/agy-ask.sh -m gemini-3.8-flash-low \
  -s '{"type":"object","properties":{"failed":{"type":"array","items":{"type":"string"}}},"required":["failed"]}' \
  "Read logs/test-output.txt and list failing test names. Do not run anything."

# let it write exactly one file
.claude/skills/agy/scripts/agy-ask.sh -w "$PWD/docs/draft.md" "Write $PWD/docs/draft.md: ..."
```

Raw form, if you need it: `agy -p "<prompt>" --model <id> --output-format json < /dev/null`. The result is a JSON line with `response`, `structured_output`, `duration_seconds`, `usage`, and `denied_actions`.

## Models (`agy models`, checked 2026-11-03)

| id | use |
|---|---|
| `gemini-3.8-flash-medium` | default for summaries, extraction, drafts |
| `gemini-3.8-flash-low` | fastest and cheapest, for mechanical tasks (about 3 to 10 s) |
| `gemini-3.8-flash-high` | more thinking, for multi-file synthesis. About 2x slower than medium on the same task, with no visible gain on easy ones |
| `claude-sonnet-4-6`, `claude-opus-4-6-thinking`, `gpt-oss-120b-medium` | also listed, not tested here. Not the default: if the task needs them it is probably too complex to delegate |

If a model id disappears, run `agy models` and pick the nearest Flash tier. Reasoning effort can also be set with `--effort low|medium|high|xhigh|max`.

## Permissions (tested behaviour)

- **Reading workspace files works with no flags.**
- **Writes and shell commands are auto-denied in headless mode.** agy then returns an empty response and lists `denied_actions`; the wrapper prints `DENIED` and exits 1.
- To allow a write, pass the **exact file path** with `-w` (an `allow` rule `write_file(<abs path>)`). Globs such as `write_file(/**)` did not work.
- `--dangerously-skip-permissions` approves everything including commands. Do not use it in this repo.
- `--mode plan` makes a run read-only. `--mode accept-edits` alone did not grant writes in print mode.
- Prefer the default pattern: **agy returns text, you write the file** (or use `-w` for one path). This keeps the diff under your review.

## Gotchas

- **Piped stdin is ignored** in print mode. Put the content in a file and name the path in the prompt.
- **Always give absolute paths** when it should write; relative paths resolve against the workspace.
- `--json-schema` needs `--output-format json`. If the prompt invites tool use, the model may try a command and get denied. Say "answer from the text only, no tools" or "read only".
- A call is a fresh conversation. Continue one with `--continue` or `--conversation <id>` (the id is in the JSON result) instead of re-sending context.
- It runs in the same workspace as the one-render-at-a-time rule. agy itself is light, but do not start many calls in parallel while a render or Kokoro job is running on the 8 GB machine; run them one after another.
- Output file links in the response use `file://` URLs; ignore them.

## Verify before you trust

Delegated output is a draft. Spot check it proportionally:

- Numbers, names, dates and quotes in summaries: confirm against the source for anything that will reach narration or on-screen text. Accuracy is a shipping requirement in `docs/VISION.md`.
- Generated JSON: run the matching validator (`studio.py validate`, `motion-catalogue.py validate`, or the schema).
- Edits: read `git diff` before accepting.
- If agy returns something vague, wrong, or empty twice, stop retrying and do the task yourself. A second failed delegation costs more than doing it.
