# Custom-runtime AppSail service (Docker Image Protocol per
# https://docs.catalyst.zoho.com/en/cli/v1/add-appsail/) — Catalyst
# takes a pre-built image reference, so this is built with the REPO
# ROOT as context (not this directory), to pull in the shared app/
# package:
#
#   docker build -f iac/vendor-native/catalyst/appsail/api/Dockerfile \
#     -t invoice-ocr-pipeline-api:latest .
#
# then referenced from `catalyst appsail:add` as
# docker://localhost/invoice-ocr-pipeline-api:latest
#
# Port: main.py reads X_ZOHO_CATALYST_LISTEN_PORT itself (falls back to
# 9000) — see main.py's __main__ block. Run it directly with `python
# main.py`, not a separate uvicorn CLI invocation with a hardcoded
# --port, so the same env var Catalyst injects controls both the
# managed-runtime and Docker-image deployment paths identically.

FROM python:3.12-slim

WORKDIR /srv

COPY iac/vendor-native/catalyst/appsail/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY iac/vendor-native/catalyst/appsail/api/main.py .

EXPOSE 9000

CMD ["python", "main.py"]
