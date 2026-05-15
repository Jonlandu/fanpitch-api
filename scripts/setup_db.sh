#!/usr/bin/env bash
# Create the local Postgres role + database for FanPitch.
# Idempotent: safe to re-run.
set -euo pipefail

DB_NAME="${POSTGRES_DB:-fanpitch}"
DB_USER="${POSTGRES_USER:-fanpitch}"
DB_PASSWORD="${POSTGRES_PASSWORD:-fanpitch}"

psql -U "${PGUSER:-$(whoami)}" -d postgres <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
    CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASSWORD';
  END IF;
END
\$\$;

SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
SQL

echo "Database '$DB_NAME' ready for user '$DB_USER'."
