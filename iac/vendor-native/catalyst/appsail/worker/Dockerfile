# Custom-runtime AppSail service — see appsail/api/Dockerfile for the
# full explanation. Build from repo root:
#
#   docker build -f iac/vendor-native/catalyst/appsail/worker/Dockerfile \
#     -t invoice-ocr-pipeline-worker:latest .

FROM python:3.12-slim

WORKDIR /srv

COPY iac/vendor-native/catalyst/appsail/worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY iac/vendor-native/catalyst/appsail/worker/main.py .

ENV PORT=3000
EXPOSE 3000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
