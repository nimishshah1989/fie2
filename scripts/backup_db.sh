#!/bin/bash
# FIE v3 — Automated Database Backup to S3
# Usage: Run daily via cron or GitHub Actions
# Requires: DATABASE_URL env var, aws CLI configured

set -euo pipefail

# Configuration
S3_BUCKET="${BACKUP_S3_BUCKET:-fie2-backups}"
S3_PREFIX="db-backups"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
BACKUP_FILE="fie_v3_${TIMESTAMP}.sql.gz"

echo "[$(date)] Starting database backup..."

# Parse DATABASE_URL
if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL not set"
    exit 1
fi

# Extract connection details from DATABASE_URL
# Format: postgresql://user:password@host:port/dbname
PGUSER=$(echo "$DATABASE_URL" | sed -E 's|postgresql://([^:]+):.*|\1|')
PGPASSWORD=$(echo "$DATABASE_URL" | sed -E 's|postgresql://[^:]+:([^@]+)@.*|\1|')
PGHOST=$(echo "$DATABASE_URL" | sed -E 's|postgresql://[^@]+@([^:]+):.*|\1|')
PGPORT=$(echo "$DATABASE_URL" | sed -E 's|postgresql://[^@]+@[^:]+:([0-9]+)/.*|\1|')
PGDATABASE=$(echo "$DATABASE_URL" | sed -E 's|postgresql://[^/]+/(.+)|\1|')

# Dump database
export PGPASSWORD
pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
    --format=plain --no-owner --no-privileges | gzip > "/tmp/${BACKUP_FILE}"

FILESIZE=$(du -h "/tmp/${BACKUP_FILE}" | cut -f1)
echo "[$(date)] Backup created: ${BACKUP_FILE} (${FILESIZE})"

# Upload to S3
aws s3 cp "/tmp/${BACKUP_FILE}" "s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILE}" \
    --storage-class STANDARD_IA \
    --region ap-south-1

echo "[$(date)] Uploaded to s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILE}"

# Clean up local file
rm -f "/tmp/${BACKUP_FILE}"

# Remove old backups (keep last RETENTION_DAYS days)
# date -d works on Linux (EC2), date -v works on macOS
CUTOFF_DATE=$(date -d "-${RETENTION_DAYS} days" +%Y-%m-%d 2>/dev/null || date -v-${RETENTION_DAYS}d +%Y-%m-%d)
echo "[$(date)] Cleaning up backups older than ${CUTOFF_DATE}..."

aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/" | while read -r line; do
    FILE_DATE=$(echo "$line" | awk '{print $1}')
    FILE_NAME=$(echo "$line" | awk '{print $4}')
    if [[ "$FILE_DATE" < "$CUTOFF_DATE" ]] && [[ -n "$FILE_NAME" ]]; then
        aws s3 rm "s3://${S3_BUCKET}/${S3_PREFIX}/${FILE_NAME}" --region ap-south-1
        echo "  Deleted old backup: ${FILE_NAME}"
    fi
done

echo "[$(date)] Backup complete!"
