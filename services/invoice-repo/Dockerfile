FROM python:3.12-slim
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /srv
COPY requirements.txt .
RUN apt-get update && apt-get install -y gcc libpq-dev build-essential     && pip install --no-cache-dir -r requirements.txt     && apt-get remove -y --purge gcc build-essential     && apt-get autoremove -y     && rm -rf /var/lib/apt/lists/*
COPY app.py .
COPY alembic.ini alembic/ ./
COPY entrypoint.sh ./entrypoint.sh
ENTRYPOINT ["/srv/entrypoint.sh"]
