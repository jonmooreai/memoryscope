#!/bin/bash
# Setup automated daily backups using cron
#
# This script sets up a cron job to run daily backups.
#
# Usage:
#   ./scripts/setup_backup_cron.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_SCRIPT="${PROJECT_DIR}/scripts/backup_database.sh"

# Create cron job (runs daily at 2 AM)
CRON_TIME="0 2 * * *"
CRON_JOB="${CRON_TIME} cd ${PROJECT_DIR} && ${BACKUP_SCRIPT} >> ${PROJECT_DIR}/backups/backup.log 2>&1"

echo "Setting up automated daily backups..."
echo ""
echo "Cron job:"
echo "  ${CRON_JOB}"
echo ""

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
    echo "⚠️  Backup cron job already exists"
    read -p "Replace it? (yes/no): " REPLACE
    if [ "$REPLACE" != "yes" ]; then
        echo "Cancelled"
        exit 0
    fi
    # Remove existing job
    crontab -l 2>/dev/null | grep -v "$BACKUP_SCRIPT" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Automated backup configured"
echo ""
echo "To view cron jobs:"
echo "  crontab -l"
echo ""
echo "To remove backup cron job:"
echo "  crontab -l | grep -v 'backup_database.sh' | crontab -"

