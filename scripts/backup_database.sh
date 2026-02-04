#!/bin/bash
# Database backup script for Memory Scope API
# 
# This script creates a timestamped backup of the PostgreSQL database.
# Backups are stored in the backups/ directory with retention policy.
#
# Usage:
#   ./scripts/backup_database.sh [backup_name]
#
# Environment variables:
#   DATABASE_URL - PostgreSQL connection string
#   BACKUP_RETENTION_DAYS - Number of days to keep backups (default: 30)

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Configuration
BACKUP_DIR="${PROJECT_DIR}/backups"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="${1:-backup_${TIMESTAMP}}"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.sql.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Extract database connection info
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL not set"
    echo "   Set DATABASE_URL in .env or environment"
    exit 1
fi

# Parse DATABASE_URL (format: postgresql+psycopg://user:pass@host:port/dbname)
DB_URL=$(echo "$DATABASE_URL" | sed 's|postgresql+psycopg://||')
DB_USER=$(echo "$DB_URL" | cut -d: -f1)
DB_PASS=$(echo "$DB_URL" | cut -d: -f2 | cut -d@ -f1)
DB_HOST_PORT=$(echo "$DB_URL" | cut -d@ -f2 | cut -d/ -f1)
DB_HOST=$(echo "$DB_HOST_PORT" | cut -d: -f1)
DB_PORT=$(echo "$DB_HOST_PORT" | cut -d: -f2)
DB_NAME=$(echo "$DB_URL" | cut -d/ -f2)

# Default port if not specified
DB_PORT="${DB_PORT:-5432}"

echo "=========================================="
echo "Database Backup"
echo "=========================================="
echo ""
echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "Backup file: $BACKUP_FILE"
echo ""

# Check if pg_dump is available
if command -v pg_dump &> /dev/null; then
    PG_DUMP_CMD="pg_dump"
elif [ -f "/opt/homebrew/Cellar/libpq/17.5/bin/pg_dump" ]; then
    PG_DUMP_CMD="/opt/homebrew/Cellar/libpq/17.5/bin/pg_dump"
else
    echo "❌ ERROR: pg_dump not found"
    echo "   Install PostgreSQL client tools"
    exit 1
fi

# Create backup
echo "Creating backup..."
export PGPASSWORD="$DB_PASS"
$PG_DUMP_CMD \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    | gzip > "$BACKUP_FILE"

unset PGPASSWORD

# Check backup success
if [ $? -eq 0 ] && [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup created successfully"
    echo "   File: $BACKUP_FILE"
    echo "   Size: $BACKUP_SIZE"
    echo ""
    
    # Clean old backups
    echo "Cleaning backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
    echo "✅ Cleanup complete"
    echo ""
    
    # List recent backups
    echo "Recent backups:"
    ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null | tail -5 | awk '{print "   " $9 " (" $5 ")"}'
    
    exit 0
else
    echo "❌ Backup failed"
    exit 1
fi

