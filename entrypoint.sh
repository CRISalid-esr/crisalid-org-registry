#!/bin/bash

docker-entrypoint.sh postgres &

until pg_isready -h localhost -U postgres; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

python3 /import_data.py

postgrest /postgrest.conf
