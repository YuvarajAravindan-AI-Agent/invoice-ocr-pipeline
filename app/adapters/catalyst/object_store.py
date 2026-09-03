"""ObjectStore implemented against Catalyst Stratus.

Grounded against docs.catalyst.zoho.com/en/sdk/python/v1/cloud-scale/
stratus/{upload-object,download-object}/ (checked 2026-09-03):
  bucket.put_object(key, body, options)
  bucket.get_object(key)
  bucket.generate_presigned_url(key, url_action='GET', expiry_in_sec=N)

Requires the STRATUS_BUCKET env var (set in appsail app-config.json —
see iac/vendor-native/catalyst/README.md).
"""

from __future__ import annotations

import os

import zcatalyst_sdk


class CatalystStratusObjectStore:
    def __init__(self) -> None:
        app = zcatalyst_sdk.initialize()
        bucket_name = os.environ["STRATUS_BUCKET"]
        self._bucket = app.stratus().bucket(bucket_name)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._bucket.put_object(key, data, {"content_type": content_type, "overwrite": "true"})

    def get(self, key: str) -> bytes:
        response = self._bucket.get_object(key)
        # NOTE: the exact attribute holding the byte content wasn't
        # confirmed from public docs — verify against the actual SDK
        # response object (likely .content or .read()) before relying on
        # this in production.
        return response.content

    def url_for(self, key: str) -> str:
        response = self._bucket.generate_presigned_url(key, url_action="GET", expiry_in_sec="300")
        return response["url"] if isinstance(response, dict) else response.url
