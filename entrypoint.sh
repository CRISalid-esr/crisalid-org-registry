#!/bin/bash
set -euo pipefail

MARKER="/var/lib/postgresql/data/.org_registry_import_done"
REFRESH="${REFRESH_ORG_REGISTRY:-0}"

docker-entrypoint.sh postgres &

until pg_isready -h localhost -U postgres; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

if [[ "$REFRESH" == "1" || ! -f "$MARKER" ]]; then
  echo "Importing org registry data (REFRESH_ORG_REGISTRY=$REFRESH)..."
  python3 /import_data.py
  touch "$MARKER"
else
  echo "Skipping import (marker exists, REFRESH_ORG_REGISTRY=$REFRESH)."
fi

exec postgrest /postgrest.conf
