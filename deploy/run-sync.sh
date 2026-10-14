#!/usr/bin/env bash
# Linux host runner. Invoke through bash; no executable-bit dependency.
set -Eeuo pipefail
umask 077

BASE_DIR="${NIMBUS_BASE_DIR:-/opt/nimbus-47}"
IMAGE="${NIMBUS_IMAGE:-nimbus-47:latest}"
ENV_FILE="$BASE_DIR/secrets/runtime.env"
mkdir -p "$BASE_DIR/state" "$BASE_DIR/data" "$BASE_DIR/logs" "$BASE_DIR/artifacts"

# Lock the entire scrape + upload operation, not only the state update.
exec 9>"$BASE_DIR/job.lock"
if ! flock -n 9; then
    echo 'Another daily job is already running.' >&2
    exit 75
fi
if [[ ! -f "$ENV_FILE" ]]; then
    echo 'Missing secrets/runtime.env.' >&2
    exit 1
fi

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
STARTED_AT="$(date -u +%FT%TZ)"
LOG_FILE="$BASE_DIR/logs/$RUN_ID.log"
echo "Started UTC=$STARTED_AT image=$IMAGE" >"$LOG_FILE"
set +e
docker run --rm \
    --user "$(id -u):$(id -g)" \
    --env-file "$ENV_FILE" \
    -e DATA_DIR=/data/articles -e STATE_DIR=/state -e TZ=UTC \
    --mount "type=bind,src=$BASE_DIR/state,dst=/state" \
    --mount "type=bind,src=$BASE_DIR/data,dst=/data" \
    "$IMAGE" --sync >>"$LOG_FILE" 2>&1
RESULT=$?
set -e
FINISHED_AT="$(date -u +%FT%TZ)"
echo "Finished UTC=$FINISHED_AT exit_code=$RESULT" >>"$LOG_FILE"

# Export only a reviewed summary, never the manifest, .env or full API response.
python3 - "$BASE_DIR" "$RUN_ID" "$STARTED_AT" "$FINISHED_AT" "$RESULT" <<'PY'
import json
import sys
from pathlib import Path

base, run_id, started, finished, exit_code = sys.argv[1:]
root = Path(base)
artifact = {'run_id': run_id, 'started_at': started, 'finished_at': finished,
            'exit_code': int(exit_code), 'execution_environment': 'host-runner',
            'status': 'success' if exit_code == '0' else 'failed'}
if exit_code == '0':
    report = json.loads((root/'state/sync-report.json').read_text(encoding='utf-8'))
    for field in ('completed_at', 'added', 'updated', 'skipped', 'uploaded_files',
                  'source_articles', 'indexed_files', 'usage_bytes'):
        artifact[field] = report[field]
target = root/'artifacts'/f'{run_id}.json'
target.write_text(json.dumps(artifact, indent=2) + '\n', encoding='utf-8')
(root/'artifacts/latest-run.json').write_text(target.read_text(encoding='utf-8'), encoding='utf-8')
PY

# Retain detailed logs for 14 days; preserve summaries for submission evidence.
find "$BASE_DIR/logs" -maxdepth 1 -type f -name '*.log' -mtime +14 -delete
cat "$LOG_FILE"
exit "$RESULT"
