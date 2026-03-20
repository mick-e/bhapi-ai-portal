#!/bin/sh
set -e

# Run migrations (best-effort — app starts even if migrations fail)
alembic upgrade head || echo "WARNING: alembic migration failed, starting anyway"

# Dispatch based on command
case "$1" in
  web)
    exec uvicorn src.main:app --host 0.0.0.0 --port 8000
    ;;
  *)
    # For cron jobs or custom commands, execute directly
    exec "$@"
    ;;
esac
