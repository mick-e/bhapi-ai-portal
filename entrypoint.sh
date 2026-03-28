#!/bin/sh
set -e

case "$1" in
  web)
    # Run migrations only for web service (best-effort)
    alembic upgrade head || echo "WARNING: alembic migration failed, starting anyway"
    exec uvicorn src.main:app --host 0.0.0.0 --port 8000
    ;;
  *)
    # Cron jobs and custom commands — skip migrations, execute directly
    exec "$@"
    ;;
esac
