#!/bin/sh
set -e
# run migrations
alembic -c /srv/alembic.ini upgrade head || true
# start app
exec uvicorn app:app --host 0.0.0.0 --port 8000
