#!/usr/bin/env bash
# Contract test: run the dev server behind `prism proxy` and drive every
# operation in contracts/blueflow/openapi.yaml through it. Prism validates each
# request/response against the spec and reports drift in `sl-violations`.
#
# Required env: BLUEFLOW_API_TOKEN (admin user's DRF token),
#               BLUEFLOW_USERNAME / BLUEFLOW_PASSWORD (same user, for login cases).
# Optional env: SERVER_PORT (8000), PRISM_PORT (4010), CONTRACT_OUT_DIR.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SPEC="contracts/blueflow/openapi.yaml"
CASES="contracts/fixtures/blueflow/cases.yaml"
MANAGE="project/manage.py"
SERVER_PORT="${SERVER_PORT:-8000}"
PRISM_PORT="${PRISM_PORT:-4010}"
SERVER_URL="http://127.0.0.1:${SERVER_PORT}"
PRISM_URL="http://127.0.0.1:${PRISM_PORT}"
OUT_DIR="${CONTRACT_OUT_DIR:-/tmp/blueflow-contract}"
SERVER_PID=""
PRISM_PID=""
PASSED=0
FAILED=0

pass() { echo "PASS: $1"; PASSED=$((PASSED + 1)); }
fail() { echo "FAIL: $1"; FAILED=$((FAILED + 1)); }

cleanup() {
  for pid in "$PRISM_PID" "$SERVER_PID"; do
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT

# --- preflight: report every problem before exiting ---------------------------
missing=0
for tool in prism uv curl jq yq; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "missing tool: $tool" >&2
    missing=1
  fi
done
for file in "$MANAGE" "$SPEC" "$CASES"; do
  if [[ ! -f "$file" ]]; then
    echo "missing file: $file" >&2
    missing=1
  fi
done
for var in BLUEFLOW_API_TOKEN BLUEFLOW_USERNAME BLUEFLOW_PASSWORD; do
  if [[ -z "${!var:-}" ]]; then
    echo "missing env var: $var" >&2
    missing=1
  fi
done
for port in "$SERVER_PORT" "$PRISM_PORT"; do
  if [[ "$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 1 "http://127.0.0.1:${port}/" || true)" != "000" ]]; then
    echo "port in use: $port" >&2
    missing=1
  fi
done
if [[ "$missing" -ne 0 ]]; then
  echo "Preflight failed." >&2
  exit 1
fi

# --- coverage gate: every spec operation needs a case --------------------------
uncovered="$(comm -23 \
  <(yq '.paths[][] | .operationId' "$SPEC" | sort -u) \
  <(yq '.[].op' "$CASES" | sort -u))"
if [[ -n "$uncovered" ]]; then
  echo "Operations in $SPEC with no case in $CASES:" >&2
  echo "$uncovered" | sed 's/^/  /' >&2
  exit 1
fi

# --- start server (dev mode) and prism ------------------------------------------
mkdir -p "$OUT_DIR"
export DJANGO_SETTINGS_MODULE=project.settings.development

wait_for() { # url pid name
  for _ in $(seq 1 60); do
    if [[ "$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 2 "$1" || true)" != "000" ]]; then
      return 0
    fi
    if ! kill -0 "$2" 2>/dev/null; then
      echo "$3 exited during startup; see $OUT_DIR/$3.log" >&2
      exit 1
    fi
    sleep 1
  done
  echo "$3 did not respond at $1; see $OUT_DIR/$3.log" >&2
  exit 1
}

# run the venv python directly: `uv run` doesn't pass SIGTERM to its child
PYTHON="$(uv run python -c 'import sys; print(sys.executable)')"
"$PYTHON" "$MANAGE" migrate --noinput >"$OUT_DIR/migrate.log" 2>&1
"$PYTHON" "$MANAGE" runserver --noreload "127.0.0.1:${SERVER_PORT}" >"$OUT_DIR/server.log" 2>&1 &
SERVER_PID=$!
wait_for "$SERVER_URL/" "$SERVER_PID" server

prism proxy "$SPEC" "$SERVER_URL" --host 127.0.0.1 --port "$PRISM_PORT" >"$OUT_DIR/prism.log" 2>&1 &
PRISM_PID=$!
wait_for "$PRISM_URL/" "$PRISM_PID" prism

# --- run cases --------------------------------------------------------------------
# operationId -> "METHOD path", read once from the spec
OPS="$(yq -o=json -I0 '[.paths | to_entries[] | .key as $p | .value | to_entries[]
  | {"key": .value.operationId, "value": {"method": (.key | upcase), "path": $p}}] | from_entries' "$SPEC")"
# captured values; JSON so it works on macOS bash 3.2 (no associative arrays)
VARS="$(jq -nc --arg run_id "$(date +%s)" --arg base_url "$SERVER_URL" '{$run_id, $base_url}')"
HEADERS="$OUT_DIR/headers"
BODY="$OUT_DIR/body"

count="$(yq 'length' "$CASES")"
for ((i = 0; i < count; i++)); do
  # fill placeholders; a string that is exactly "{var}" keeps the var's type
  case_json="$(yq -o=json -I0 ".[$i]" "$CASES" | jq -c --argjson vars "$VARS" '
    def sub: gsub("\\{(?<k>[A-Za-z_:]+)\\}";
      if .k | startswith("env:") then $ENV[.k[4:]] // "" else $vars[.k] // "{\(.k)}" | tostring end);
    walk(if type == "string" then
      (capture("^\\{(?<k>[A-Za-z_]+)\\}$") as $m | $vars[$m.k] // .) // . | if type == "string" then sub else . end
    else . end)')"
  op="$(jq -r '.op' <<<"$case_json")"
  method="$(jq -r --arg op "$op" '.[$op].method' <<<"$OPS")"
  url="$(jq -r --argjson c "$case_json" --arg base "$PRISM_URL" '
    reduce ($c.path // {} | to_entries[]) as $e (.[$c.op].path; gsub("\\{\($e.key)\\}"; $e.value | tostring))
    | $base + . + (if $c.query then "?" + ($c.query | to_entries | map("\(.key)=\(.value | tostring | @uri)") | join("&")) else "" end)' <<<"$OPS")"

  args=(-s -X "$method" -D "$HEADERS" -o "$BODY" -w '%{http_code}')
  if [[ "$(jq -r '.auth // ""' <<<"$case_json")" != "none" ]]; then
    args+=(-H "Authorization: Token ${BLUEFLOW_API_TOKEN}")
  fi
  if jq -e 'has("form")' <<<"$case_json" >/dev/null; then
    while IFS= read -r field; do args+=(-F "$field"); done \
      < <(jq -r '.form | to_entries[] | "\(.key)=\(.value)"' <<<"$case_json")
  elif jq -e 'has("body")' <<<"$case_json" >/dev/null; then
    args+=(-H "Content-Type: application/json" --data-binary "$(jq -c '.body' <<<"$case_json")")
  fi

  label="$op ($method ${url#"$PRISM_URL"})"
  code="$(curl "${args[@]}" "$url" || echo 000)"
  violations="$(sed -n 's/^[Ss][Ll]-[Vv]iolations: *//p' "$HEADERS" 2>/dev/null | tr -d '\r')"

  if [[ -n "$violations" ]]; then
    fail "$label -> $code, contract violations:"
    jq -r '.[] | "    - [\(.severity // "error")] \(.location // [] | join(".")): \(.message)"' <<<"$violations" \
      || echo "    $violations"
  elif jq -e --argjson code "$code" '(.expect // []) as $e
      | if ($e | length) > 0 then $e | index($code) != null else $code >= 200 and $code < 300 end' \
      <<<"$case_json" >/dev/null; then
    pass "$label -> $code"
  else
    fail "$label -> $code, unexpected status"
    head -c 500 "$BODY" | sed 's/^/    /'
    echo
  fi

  if jq -e 'has("save")' <<<"$case_json" >/dev/null; then
    saved="$(jq -c --argjson c "$case_json" --slurpfile body "$BODY" '
      $c.save | with_entries(.value as $p | .value = ($body[0] | getpath($p | ltrimstr(".") | split("."))))
      | select(all(.[]; . != null))' <<<"null" 2>/dev/null || true)"
    if [[ -n "$saved" ]]; then
      VARS="$(jq -c --argjson s "$saved" '. + $s' <<<"$VARS")"
    else
      echo "    could not capture $(jq -c '.save' <<<"$case_json") from response; dependent cases will fail"
    fi
  fi
done

echo ""
echo "${PASSED} passed / ${FAILED} failed (logs in $OUT_DIR)"
[[ "$FAILED" -eq 0 ]]
