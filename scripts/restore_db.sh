#!/bin/bash
# FIE v3 — Restore Database from S3 Backup
# Usage: ./scripts/restore_db.sh [backup_filename]
# If no filename specified, lists available backups

set -euo pipefail

S3_BUCKET="${BACKUP_S3_BUCKET:-fie2-backups}"
S3_PREFIX="db-backups"

if [ -z "${1:-}" ]; then
    echo "Available backups:"
    aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/" --region ap-south-1 | sort -r | head -20
    echo ""
    echo "Usage: $0 <backup_filename>"
    echo "Example: $0 fie_v3_2026-03-07_183000.sql.gz"
    exit 0
fi

BACKUP_FILE="$1"

if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL not set"
    exit 1
fi

echo "WARNING: This will overwrite the current database!"
echo "Backup: ${BACKUP_FILE}"
read -p "Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# Download from S3
echo "Downloading backup..."
aws s3 cp "s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILE}" "/tmp/${BACKUP_FILE}" --region ap-south-1

# Parse DATABASE_URL
PGUSER=$(echo "$DATABASE_URL" | sed -E 's|postgresql://([^:]+):.*|\1|')
PGPASSWORD=$(echo "$DATABASE_URL" | sed -E 's|postgresql://[^:]+:([^@]+)@.*|\1|')
PGHOST=$(echo "$DATABASE_URL" | sed -E 's|postgresql://[^@]+@([^:]+):.*|\1|')
PGPORT=$(echo "$DATABASE_URL" | sed -E 's|postgresql://[^@]+@[^:]+:([0-9]+)/.*|\1|')
PGDATABASE=$(echo "$DATABASE_URL" | sed -E 's|postgresql://[^/]+/(.+)|\1|')

export PGPASSWORD

# Restore
echo "Restoring database..."
gunzip -c "/tmp/${BACKUP_FILE}" | psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" --quiet

# Clean up
rm -f "/tmp/${BACKUP_FILE}"

echo "Restore complete!"
