# Custom-runtime AppSail service — see appsail/api/Dockerfile for the
# full explanation, including why CMD runs main.py directly instead of
# a uvicorn CLI invocation with a hardcoded --port. Build from repo root:
#
#   docker build -f iac/vendor-native/catalyst/appsail/worker/Dockerfile \
#     -t invoice-ocr-pipeline-worker:latest .

FROM python:3.12-slim

WORKDIR /srv

COPY iac/vendor-native/catalyst/appsail/worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY iac/vendor-native/catalyst/appsail/worker/main.py .

EXPOSE 9000

CMD ["python", "main.py"]
