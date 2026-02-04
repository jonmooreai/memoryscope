#!/bin/bash
# Run database migration using alembic
# This script handles the local alembic directory shadowing issue

set -e

cd "$(dirname "$0")"

echo "Running database migration..."
echo ""

# Use Python to run alembic, avoiding the local alembic directory
python3 -c "
import sys
import os

# Remove current directory from path to avoid local alembic shadowing
sys.path = [p for p in sys.path if os.path.abspath(p) != os.path.abspath('.')]

from alembic.config import Config
from alembic import command

cfg = Config('alembic.ini')
command.upgrade(cfg, 'head')
"

echo ""
echo "✅ Migration complete!"

