#!/bin/bash
# Database restore script for Memory Scope API
#
# This script restores a database from a backup file.
#
# Usage:
#   ./scripts/restore_database.sh <backup_file>
#
# WARNING: This will overwrite the current database!

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check arguments
if [ -z "$1" ]; then
    echo "❌ ERROR: Backup file required"
    echo ""
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lh backups/*.sql.gz 2>/dev/null | awk '{print "   " $9}'
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Extract database connection info
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL not set"
    exit 1
fi

DB_URL=$(echo "$DATABASE_URL" | sed 's|postgresql+psycopg://||')
DB_USER=$(echo "$DB_URL" | cut -d: -f1)
DB_PASS=$(echo "$DB_URL" | cut -d: -f2 | cut -d@ -f1)
DB_HOST_PORT=$(echo "$DB_URL" | cut -d@ -f2 | cut -d/ -f1)
DB_HOST=$(echo "$DB_HOST_PORT" | cut -d: -f1)
DB_PORT=$(echo "$DB_HOST_PORT" | cut -d: -f2)
DB_NAME=$(echo "$DB_URL" | cut -d/ -f2)

DB_PORT="${DB_PORT:-5432}"

echo "=========================================="
echo "Database Restore"
echo "=========================================="
echo ""
echo "⚠️  WARNING: This will overwrite the current database!"
echo ""
echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "Backup file: $BACKUP_FILE"
echo ""

# Confirm
read -p "Are you sure you want to continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

# Check if psql is available
if command -v psql &> /dev/null; then
    PSQL_CMD="psql"
elif [ -f "/opt/homebrew/Cellar/libpq/17.5/bin/psql" ]; then
    PSQL_CMD="/opt/homebrew/Cellar/libpq/17.5/bin/psql"
else
    echo "❌ ERROR: psql not found"
    exit 1
fi

# Restore backup
echo "Restoring backup..."
export PGPASSWORD="$DB_PASS"

# Check if file is gzipped
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | $PSQL_CMD \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME"
else
    $PSQL_CMD \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        < "$BACKUP_FILE"
fi

unset PGPASSWORD

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database restored successfully"
    exit 0
else
    echo ""
    echo "❌ Restore failed"
    exit 1
fi

