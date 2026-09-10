#!/bin/sh
set -e

# If DATABASE_URL points to a DB, wait until it's reachable
if [ "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL present, waiting for DB..."
  python - <<'PYCODE'
import os, time
from sqlalchemy import create_engine
url = os.getenv('DATABASE_URL')
for i in range(30):
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            print('DB reachable')
            break
    except Exception as e:
        print('DB not ready, retrying...', e)
        time.sleep(1)
else:
    print('DB did not become ready in time')
    raise SystemExit(1)
PYCODE
fi

# run migrations
alembic -c /srv/alembic.ini upgrade head || true

# start app
exec uvicorn app:app --host 0.0.0.0 --port 8000
