"""ObjectStore implemented against Catalyst Stratus.

Grounded against docs.catalyst.zoho.com/en/sdk/python/v1/cloud-scale/
stratus/{upload-object,download-object}/ (checked 2026-09-03):
  bucket.put_object(key, body, options)
  bucket.get_object(key)
  bucket.generate_presigned_url(key, url_action='GET', expiry_in_sec=N)

Requires the STRATUS_BUCKET env var (set in appsail app-config.json —
see iac/vendor-native/catalyst/README.md).

Takes an already-initialized CatalystApp rather than calling
zcatalyst_sdk.initialize() itself — per Zoho's own Flask example
(docs.catalyst.zoho.com/en/serverless/help/appsail/help-guides/python/
flask/), initialize() must be called **per request** with
`req=<request object>`, not once at import time with no arguments.
See main.py's get_catalyst_app dependency for where this happens.
"""

from __future__ import annotations

import os


class CatalystStratusObjectStore:
    def __init__(self, catalyst_app) -> None:
        bucket_name = os.environ["STRATUS_BUCKET"]
        self._bucket = catalyst_app.stratus().bucket(bucket_name)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._bucket.put_object(key, data, {"content_type": content_type, "overwrite": "true"})

    def get(self, key: str) -> bytes:
        # Confirmed against the real SDK response (not docs): get_object()
        # returns raw bytes directly, not a response wrapper with a
        # .content attribute — a real AttributeError caught via the
        # worker's /process pipeline showed this.
        return self._bucket.get_object(key)

    def url_for(self, key: str) -> str:
        response = self._bucket.generate_presigned_url(key, url_action="GET", expiry_in_sec="300")
        return response["url"] if isinstance(response, dict) else response.url
