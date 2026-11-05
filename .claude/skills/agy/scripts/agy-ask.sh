#!/usr/bin/env bash
# Headless wrapper around the Antigravity CLI (agy) for delegated, low-complexity work.
# Usage: agy-ask.sh [-m MODEL] [-w EXACT_FILE]... [-s SCHEMA_JSON_OR_PATH] "prompt"
#   -m  model id (default gemini-3.8-flash-medium; see `agy models`)
#   -w  exact file path agy may write (repeatable; globs are NOT honoured by agy)
#   -s  JSON schema (inline or file path); the validated object is printed instead of prose
# Prints the response on stdout, and a one-line usage summary on stderr.
set -euo pipefail

MODEL="gemini-3.8-flash-medium"
SCHEMA=""
WRITES=()
while getopts "m:w:s:" opt; do
  case "$opt" in
    m) MODEL="$OPTARG" ;;
    w) WRITES+=("$OPTARG") ;;
    s) SCHEMA="$OPTARG" ;;
    *) echo "usage: agy-ask.sh [-m model] [-w file]... [-s schema] prompt" >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))
PROMPT="${1:?prompt required}"

ARGS=(-p "$PROMPT" --model "$MODEL" --output-format json)
[ -n "$SCHEMA" ] && ARGS+=(--json-schema "$SCHEMA")
if [ "${#WRITES[@]}" -gt 0 ]; then
  SETTINGS=$(python3 -c 'import json,sys; print(json.dumps({"permissions":{"allow":["write_file(%s)" % p for p in sys.argv[1:]]}}))' "${WRITES[@]}")
  ARGS+=(--settings "$SETTINGS")
fi

# stdin must be closed or agy can block waiting on it.
RAW=$(agy "${ARGS[@]}" < /dev/null 2>&1) || true

printf '%s' "$RAW" | python3 -c '
import json, sys
raw = sys.stdin.read()
doc = None
for line in reversed(raw.strip().splitlines()):
    try:
        doc = json.loads(line)
        break
    except ValueError:
        continue
if doc is None:
    sys.exit("agy-ask: no JSON result from agy:\n" + raw[:2000])
if doc.get("denied_actions"):
    names = ", ".join(a.get("display_name", a.get("action", "?")) for a in doc["denied_actions"])
    sys.stderr.write("agy-ask: DENIED " + names + " (grant with -w <exact file>; commands are never granted)\n")
out = doc.get("structured_output")
print(json.dumps(out, indent=2) if out is not None else doc.get("response", "").rstrip())
u = doc.get("usage", {})
sys.stderr.write("agy-ask: %s %.1fs in=%s out=%s\n" % (doc.get("status"), doc.get("duration_seconds", 0), u.get("input_tokens"), u.get("output_tokens")))
if doc.get("status") != "SUCCESS" or (not doc.get("response") and out is None):
    sys.exit(1)
'
